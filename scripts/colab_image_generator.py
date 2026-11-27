#!/usr/bin/env python3
"""
Google Colab T4 FLUX.2-klein-4B hero image generator for honda.cat.

Provisions an ephemeral Colab GPU session via `google-colab-cli`, runs
two-stage 4-bit FP16/BF16 image-conditioned generation for one or more
hero image jobs in a single session, downloads optimized 1200x675 WebP
files, and guarantees runtime teardown in `finally`.
"""

from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import resources
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Iterator
import uuid

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "honda-cat"
DEFAULT_ADC_PATH = DEFAULT_CONFIG_DIR / "colab_adc.json"
DEFAULT_PKCE_PATH = DEFAULT_CONFIG_DIR / "oauth_pkce.json"
DEFAULT_COLAB_GPU = "T4"

REMOTE_WORKER_SCRIPT = r'''#!/usr/bin/env python3
"""Remote Colab worker for two-stage FLUX.2-klein-4B hero image generation."""

import argparse
import gc
import json
import os
from pathlib import Path
import shutil
import time
import traceback

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
from PIL import Image
import torch

CONTENT_DIR = Path("/content")
JOBS_PATH = CONTENT_DIR / "hero_jobs.json"
EMBEDS_PATH = CONTENT_DIR / "hero_embeds.pt"
RESULTS_PATH = CONTENT_DIR / "hero_results.json"
HF_HUB_CACHE = Path(os.path.expanduser("~/.cache/huggingface/hub"))
MODEL_ID = "black-forest-labs/FLUX.2-klein-4B"


def cleanup(pipe=None, clear_hf_cache: bool = False) -> None:
    if pipe is not None:
        del pipe
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    if clear_hf_cache and HF_HUB_CACHE.exists():
        shutil.rmtree(HF_HUB_CACHE, ignore_errors=True)


def resolve_dtype() -> torch.dtype:
    if not torch.cuda.is_available():
        return torch.float32
    cc_major, _ = torch.cuda.get_device_capability(0)
    return torch.float16 if cc_major < 8 else torch.bfloat16


def make_quant_config(components: list[str], dtype: torch.dtype):
    from diffusers import PipelineQuantizationConfig

    return PipelineQuantizationConfig(
        quant_backend="bitsandbytes_4bit",
        quant_kwargs={
            "load_in_4bit": True,
            "bnb_4bit_quant_type": "nf4",
            "bnb_4bit_compute_dtype": dtype,
        },
        components_to_quantize=components,
    )


def run_encode() -> None:
    from diffusers import Flux2KleinPipeline

    jobs = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    dtype = resolve_dtype()
    t0 = time.perf_counter()
    pipe = Flux2KleinPipeline.from_pretrained(
        MODEL_ID,
        transformer=None,
        vae=None,
        quantization_config=make_quant_config(["text_encoder"], dtype),
        dtype=dtype,
    )
    pipe.enable_model_cpu_offload()
    print(f"[colab-worker:encode] Loaded text_encoder in {time.perf_counter() - t0:.1f}s (dtype={dtype})", flush=True)

    encoded: dict[str, torch.Tensor] = {}
    try:
        with torch.inference_mode():
            for job in jobs:
                slug = job["slug"]
                pe, _ = pipe.encode_prompt(prompt=job["prompt"], device="cuda")
                encoded[slug] = pe.cpu()
                print(f"[colab-worker:encode] Encoded '{slug}'", flush=True)
        torch.save(encoded, EMBEDS_PATH)
    finally:
        cleanup(pipe, clear_hf_cache=False)


def run_generate() -> None:
    from diffusers import Flux2KleinPipeline

    jobs = json.loads(JOBS_PATH.read_text(encoding="utf-8"))
    encoded = torch.load(EMBEDS_PATH, map_location="cpu")
    dtype = resolve_dtype()

    t0 = time.perf_counter()
    pipe = Flux2KleinPipeline.from_pretrained(
        MODEL_ID,
        text_encoder=None,
        quantization_config=make_quant_config(["transformer"], dtype),
        dtype=dtype,
    )
    pipe.enable_model_cpu_offload()
    load_s = round(time.perf_counter() - t0, 2)
    print(f"[colab-worker:generate] Loaded transformer+vae in {load_s}s (dtype={dtype})", flush=True)

    results: dict[str, dict] = {
        "model_id": MODEL_ID,
        "dtype": str(dtype),
        "load_seconds": load_s,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "jobs": {},
    }

    try:
        for job in jobs:
            slug = job["slug"]
            ref_path = CONTENT_DIR / job["ref_file"]
            out_path = CONTENT_DIR / job["output_file"]
            seed = int(job.get("seed", 42))
            try:
                with Image.open(ref_path) as im:
                    ref_img = im.convert("RGB").resize((512, 512), Image.Resampling.LANCZOS)

                t_img = time.perf_counter()
                with torch.inference_mode():
                    out = pipe(
                        image=[ref_img],
                        prompt_embeds=encoded[slug].to("cuda"),
                        width=1280,
                        height=720,
                        guidance_scale=1.0,
                        num_inference_steps=4,
                        generator=torch.Generator(device="cpu").manual_seed(seed),
                    ).images[0]
                elapsed = round(time.perf_counter() - t_img, 2)

                if out.mode in ("RGBA", "P"):
                    out = out.convert("RGB")
                pixel_mean = round(float(np.asarray(out).mean()), 2)
                if pixel_mean < 1.0:
                    raise RuntimeError(f"Generated near-black image (pixel_mean={pixel_mean})")

                if out.width != 1200:
                    target_h = int(round(out.height * (1200 / out.width)))
                    out = out.resize((1200, target_h), Image.Resampling.LANCZOS)
                out.save(out_path, format="WEBP", quality=85, method=6)
                size_kb = out_path.stat().st_size // 1024

                results["jobs"][slug] = {
                    "status": "ok",
                    "output_file": out_path.name,
                    "seconds": elapsed,
                    "size_kb": size_kb,
                    "pixel_mean": pixel_mean,
                    "seed": seed,
                }
                print(
                    f"[colab-worker:generate] '{slug}' ok in {elapsed}s ({size_kb} KB, mean={pixel_mean})",
                    flush=True,
                )
            except Exception as job_err:
                tb = traceback.format_exc()
                results["jobs"][slug] = {
                    "status": "error",
                    "error": str(job_err),
                    "traceback": tb,
                }
                print(f"[colab-worker:generate] '{slug}' failed: {job_err}", flush=True)
        if torch.cuda.is_available():
            results["peak_vram_gb"] = round(torch.cuda.max_memory_allocated() / (1024**3), 2)
    finally:
        RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
        EMBEDS_PATH.unlink(missing_ok=True)
        cleanup(pipe, clear_hf_cache=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["encode", "generate"], required=True)
    args = parser.parse_args()
    if args.stage == "encode":
        run_encode()
    else:
        run_generate()


if __name__ == "__main__":
    main()
'''


@dataclass
class HeroImageJob:
    slug: str
    featured_cat: str
    ref_image_path: Path
    prompt: str
    output_webp_path: Path
    seed: int = 42


def find_colab_cli() -> str | None:
    """Locate the `colab` CLI executable in the current Python env or PATH."""
    venv_candidate = Path(sys.executable).parent / "colab"
    if venv_candidate.exists() and os.access(venv_candidate, os.X_OK):
        return str(venv_candidate)
    return shutil.which("colab")


def _parse_adc_json_payload(raw_value: str) -> str | None:
    stripped = raw_value.strip()
    if not stripped:
        return None
    if stripped.startswith("{"):
        data = json.loads(stripped)
    else:
        decoded = base64.b64decode(stripped).decode("utf-8")
        data = json.loads(decoded)
    if data.get("type") != "authorized_user" or not data.get("refresh_token"):
        return None
    return json.dumps(data, indent=2)


def _is_valid_adc_file(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("type") == "authorized_user" and bool(data.get("refresh_token"))
    except Exception:
        return False


def resolve_colab_adc_path() -> tuple[Path | None, bool]:
    """
    Resolve Colab ADC credential JSON path.

    Returns `(path, is_temp_file)`. Precedence:
      1. `COLAB_ADC_JSON` env var (raw JSON or base64 JSON)
      2. `COLAB_ADC_PATH` env var
      3. `GOOGLE_APPLICATION_CREDENTIALS` env var (if `authorized_user`)
      4. `~/.config/honda-cat/colab_adc.json`
    """
    raw_env = os.environ.get("COLAB_ADC_JSON", "").strip()
    if raw_env:
        try:
            normalized = _parse_adc_json_payload(raw_env)
            if normalized:
                fd, tmp_name = tempfile.mkstemp(prefix="honda_cat_colab_adc_", suffix=".json")
                tmp_path = Path(tmp_name)
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(normalized)
                os.chmod(tmp_path, 0o600)
                return tmp_path, True
        except Exception as exc:
            print(f"⚠️ Invalid COLAB_ADC_JSON environment payload: {exc}")

    for candidate in (
        os.environ.get("COLAB_ADC_PATH", "").strip(),
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip(),
        str(DEFAULT_ADC_PATH),
    ):
        if candidate:
            p = Path(candidate).expanduser()
            if _is_valid_adc_file(p):
                return p, False

    return None, False


def is_colab_configured() -> bool:
    """Return True when both `colab` CLI and Colab ADC credentials are available."""
    if not find_colab_cli():
        return False
    if os.environ.get("COLAB_ADC_JSON", "").strip():
        try:
            if _parse_adc_json_payload(os.environ["COLAB_ADC_JSON"]):
                return True
        except Exception:
            return False
    adc_path, is_tmp = resolve_colab_adc_path()
    if is_tmp and adc_path:
        adc_path.unlink(missing_ok=True)
    return adc_path is not None


@contextmanager
def _colab_adc_env() -> Iterator[tuple[str, dict[str, str]]]:
    colab_bin = find_colab_cli()
    if not colab_bin:
        raise RuntimeError("`colab` CLI not found. Install `google-colab-cli>=0.8.0`.")

    adc_path, is_temp = resolve_colab_adc_path()
    if not adc_path:
        raise RuntimeError(
            "Colab ADC credentials not configured. Run `python3 scripts/colab_image_generator.py --auth-url` "
            "or set `COLAB_ADC_JSON`."
        )

    env = os.environ.copy()
    env["GOOGLE_APPLICATION_CREDENTIALS"] = str(adc_path)
    env.setdefault("COLAB_CLI_ASSIGN_RETRIES", "3")
    env.setdefault("COLAB_CLI_RETRY_BACKOFF", "5")
    try:
        yield colab_bin, env
    finally:
        if is_temp:
            adc_path.unlink(missing_ok=True)


def _run_colab_cmd(
    colab_bin: str,
    args: list[str],
    env: dict[str, str],
    stream_output: bool = False,
    stdin_text: str | None = None,
) -> subprocess.CompletedProcess[str] | int:
    cmd = [colab_bin, "--auth=adc", *args]
    if stream_output:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if stdin_text is not None and proc.stdin is not None:
            proc.stdin.write(stdin_text)
            proc.stdin.close()
        if proc.stdout is not None:
            for line in proc.stdout:
                print(line, end="", flush=True)
        return proc.wait()

    return subprocess.run(cmd, env=env, text=True, check=True)


def generate_hero_images_batch(
    jobs: list[HeroImageJob],
    gpu: str | None = None,
) -> dict[str, Path]:
    """
    Generate multiple hero WebP images in a single ephemeral Colab GPU session.

    Returns a mapping `{job.slug: job.output_webp_path}` for every job that succeeded.
    Guarantees session termination in `finally`.
    """
    if not jobs:
        return {}

    target_gpu = (gpu or os.environ.get("COLAB_GPU") or DEFAULT_COLAB_GPU).strip()
    session_name = f"hero-flux2-{uuid.uuid4().hex[:8]}"
    generated: dict[str, Path] = {}

    with _colab_adc_env() as (colab_bin, env):
        with tempfile.TemporaryDirectory(prefix="honda_cat_colab_work_") as work_str:
            work_dir = Path(work_str)
            worker_path = work_dir / "remote_flux2_worker.py"
            worker_path.write_text(REMOTE_WORKER_SCRIPT, encoding="utf-8")

            unique_refs: dict[str, Path] = {}
            serialized_jobs: list[dict[str, object]] = []
            for job in jobs:
                if not job.ref_image_path.exists():
                    raise FileNotFoundError(f"Reference cat image not found: {job.ref_image_path}")
                ref_remote = f"ref_{job.featured_cat}.png"
                unique_refs[ref_remote] = job.ref_image_path
                serialized_jobs.append(
                    {
                        "slug": job.slug,
                        "ref_file": ref_remote,
                        "prompt": job.prompt,
                        "output_file": f"out_{job.slug}.webp",
                        "seed": job.seed,
                    }
                )

            jobs_json_path = work_dir / "hero_jobs.json"
            jobs_json_path.write_text(json.dumps(serialized_jobs, ensure_ascii=False, indent=2), encoding="utf-8")

            session_created = False
            try:
                print(f"☁️ Provisioning Colab {target_gpu} session '{session_name}' for {len(jobs)} hero image(s)...")
                _run_colab_cmd(colab_bin, ["new", "-s", session_name, "--gpu", target_gpu], env)
                session_created = True

                for remote_name, local_ref in unique_refs.items():
                    _run_colab_cmd(colab_bin, ["upload", "-s", session_name, str(local_ref), f"/content/{remote_name}"], env)
                _run_colab_cmd(colab_bin, ["upload", "-s", session_name, str(jobs_json_path), "/content/hero_jobs.json"], env)
                _run_colab_cmd(
                    colab_bin,
                    ["upload", "-s", session_name, str(worker_path), "/content/remote_flux2_worker.py"],
                    env,
                )

                print("📦 Installing FLUX.2-klein-4B runtime dependencies on Colab...")
                _run_colab_cmd(
                    colab_bin,
                    [
                        "install",
                        "-s",
                        session_name,
                        "git+https://github.com/huggingface/diffusers.git",
                        "transformers>=4.51.0",
                        "accelerate",
                        "safetensors",
                        "bitsandbytes",
                        "sentencepiece",
                        "protobuf",
                    ],
                    env,
                )

                for stage in ("encode", "generate"):
                    print(f"🚀 Running Colab FLUX.2-klein-4B stage [{stage}]...")
                    runner_code = (
                        "import subprocess, sys\n"
                        f"p = subprocess.Popen([sys.executable, '-u', '/content/remote_flux2_worker.py', '--stage', '{stage}'], "
                        "stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)\n"
                        "for line in p.stdout:\n"
                        "    print(line, end='', flush=True)\n"
                        "rc = p.wait()\n"
                        "if rc != 0:\n"
                        "    sys.exit(rc)\n"
                    )
                    rc = _run_colab_cmd(
                        colab_bin,
                        ["exec", "-s", session_name, "--timeout", "600"],
                        env,
                        stream_output=True,
                        stdin_text=runner_code,
                    )
                    if rc != 0:
                        raise RuntimeError(f"Colab remote stage '{stage}' exited with code {rc}")

                remote_results_local = work_dir / "hero_results.json"
                try:
                    _run_colab_cmd(
                        colab_bin,
                        ["download", "-s", session_name, "/content/hero_results.json", str(remote_results_local)],
                        env,
                    )
                    if remote_results_local.exists():
                        summary = json.loads(remote_results_local.read_text(encoding="utf-8"))
                        print(f"📊 Colab GPU summary: {summary.get('gpu')} | peak_vram={summary.get('peak_vram_gb')} GB")
                except Exception as exc:
                    print(f"⚠️ Could not download hero_results.json: {exc}")

                for job, job_meta in zip(jobs, serialized_jobs):
                    remote_out = f"/content/{job_meta['output_file']}"
                    job.output_webp_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        _run_colab_cmd(
                            colab_bin,
                            ["download", "-s", session_name, remote_out, str(job.output_webp_path)],
                            env,
                        )
                        if job.output_webp_path.exists() and job.output_webp_path.stat().st_size > 1024:
                            generated[job.slug] = job.output_webp_path
                            size_kb = job.output_webp_path.stat().st_size // 1024
                            print(f"✅ Downloaded Colab hero image: {job.output_webp_path} ({size_kb} KB)")
                        else:
                            print(f"⚠️ Downloaded empty/invalid hero image for '{job.slug}'")
                    except Exception as dl_err:
                        print(f"⚠️ Failed to download Colab hero image for '{job.slug}': {dl_err}")
            finally:
                if session_created:
                    print(f"🧹 Stopping Colab session '{session_name}'...")
                    try:
                        subprocess.run(
                            [colab_bin, "--auth=adc", "stop", "-s", session_name],
                            env=env,
                            text=True,
                            check=False,
                        )
                    except Exception as stop_err:
                        print(f"⚠️ Error while stopping Colab session '{session_name}': {stop_err}")

    return generated


def generate_hero_image(
    slug: str,
    featured_cat: str,
    ref_image_path: Path,
    prompt: str,
    output_webp_path: Path,
    seed: int = 42,
    gpu: str | None = None,
) -> bool:
    """Generate a single hero WebP image using an ephemeral Colab T4 session."""
    results = generate_hero_images_batch(
        [
            HeroImageJob(
                slug=slug,
                featured_cat=featured_cat,
                ref_image_path=ref_image_path,
                prompt=prompt,
                output_webp_path=output_webp_path,
                seed=seed,
            )
        ],
        gpu=gpu,
    )
    return slug in results


def _load_bundled_oauth_config() -> dict:
    config_res = resources.files("colab_cli").joinpath("oauth_config.json")
    return json.loads(config_res.read_text(encoding="utf-8"))


def _write_secure_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)


def _cmd_auth_url() -> int:
    from colab_cli.auth import PUBLIC_SCOPES, REMOTE_REDIRECT_URI
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_config(_load_bundled_oauth_config(), PUBLIC_SCOPES)
    flow.redirect_uri = REMOTE_REDIRECT_URI
    auth_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        token_usage="remote",
    )
    _write_secure_json(
        DEFAULT_PKCE_PATH,
        {"code_verifier": getattr(flow, "code_verifier", None), "state": state},
    )
    print(auth_url)
    return 0


def _cmd_auth_exchange(code: str) -> int:
    from colab_cli.auth import PUBLIC_SCOPES, REMOTE_REDIRECT_URI
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not DEFAULT_PKCE_PATH.exists():
        raise FileNotFoundError(f"PKCE state not found at {DEFAULT_PKCE_PATH}. Run --auth-url first.")

    pkce_data = json.loads(DEFAULT_PKCE_PATH.read_text(encoding="utf-8"))
    flow = InstalledAppFlow.from_client_config(_load_bundled_oauth_config(), PUBLIC_SCOPES)
    flow.redirect_uri = REMOTE_REDIRECT_URI
    if pkce_data.get("code_verifier"):
        flow.code_verifier = pkce_data["code_verifier"]

    flow.oauth2session.scope = None
    flow.fetch_token(code=code.strip())
    creds = flow.credentials

    adc_payload = {
        "type": "authorized_user",
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
    }
    _write_secure_json(DEFAULT_ADC_PATH, adc_payload)
    DEFAULT_PKCE_PATH.unlink(missing_ok=True)
    print(f"✅ Saved Colab ADC credentials to {DEFAULT_ADC_PATH}")
    return 0


def _cmd_check() -> int:
    if not is_colab_configured():
        print("❌ Colab CLI or credentials not configured.")
        return 1
    with _colab_adc_env() as (colab_bin, env):
        _run_colab_cmd(colab_bin, ["usage"], env)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Colab T4 FLUX.2-klein-4B hero image helper")
    parser.add_argument("--auth-url", action="store_true", help="Print OAuth consent URL for Colab ADC setup")
    parser.add_argument("--auth-exchange", type=str, default=None, help="Exchange OAuth authorization code and save ADC JSON")
    parser.add_argument("--check", action="store_true", help="Verify Colab ADC credentials and print Compute Unit balance")
    args = parser.parse_args()

    if args.auth_url:
        return _cmd_auth_url()
    if args.auth_exchange:
        return _cmd_auth_exchange(args.auth_exchange)
    if args.check:
        return _cmd_check()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
