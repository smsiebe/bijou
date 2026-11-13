"""
Bijou Post-Installation Lifecycle Hook.
Executed automatically by AuraSprout upon sovereign virtual environment creation.
Zero external dependencies (Python standard library only).
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def log(msg: str) -> None:
    print(f"[Bijou Hook] {msg}", flush=True)


def _env(primary: str, fallback: str, default: str) -> str:
    return os.environ.get(primary) or os.environ.get(fallback) or default


def main() -> None:
    install_dir = Path(_env("AURASPROUT_INSTALL_DIR", "AURASEED_INSTALL_DIR", ".")).resolve()
    app_root = Path(_env("AURASPROUT_APP_ROOT", "AURASEED_BUNDLE_DIR", ".")).resolve()
    artifacts_dir = Path(
        _env("AURASPROUT_ARTIFACTS_DIR", "AURASEED_ARTIFACTS_DIR", str(app_root / "artifacts"))
    ).resolve()
    python_exe = Path(_env("AURASPROUT_PYTHON", "AURASEED_PYTHON", sys.executable)).resolve()
    port = _env("AURASPROUT_PORT", "AURASEED_PORT", "8000")
    app_id = _env("AURASPROUT_APP_ID", "AURASEED_APP_NAME", "bijou")
    version = _env("AURASPROUT_VERSION", "AURASEED_VERSION", "0.1.0")

    log("=" * 60)
    log("Initializing Bijou Post-Install Environment Setup")
    log(f"Install Target: {install_dir}")
    log(f"App/Bundle Root:{app_root}")
    log(f"Artifacts Dir:  {artifacts_dir}")
    log(f"Python Binary:  {python_exe}")
    log(f"Assigned Port:  {port}")
    log("=" * 60)

    # 1. Ensure target directory structure exists
    target_datasets = install_dir / "datasets"
    target_datasets.mkdir(parents=True, exist_ok=True)

    target_configs = install_dir / "configs"
    target_configs.mkdir(parents=True, exist_ok=True)

    # 2. Deploy bundled dataset artifacts into install directory
    source_datasets = None
    for cand in [
        artifacts_dir / "datasets",
        app_root / "src" / "datasets",
        app_root / "payload" / "datasets",
        app_root / "datasets",
    ]:
        if cand.exists() and cand.is_dir():
            source_datasets = cand
            break

    if source_datasets and source_datasets.exists() and source_datasets.is_dir():
        deployed_count = 0
        for f in source_datasets.glob("*.*"):
            if f.is_file() and f.suffix.lower() in [".json", ".yaml", ".yml", ".jsonl"]:
                dest_file = target_datasets / f.name
                shutil.copy2(f, dest_file)
                deployed_count += 1
        log(f"Deployed {deployed_count} reference architecture datasets to {target_datasets}")

    # 3. Environment & Network Profile Configuration
    net_profile = os.environ.get("BIJOU_NET_PROFILE", "default")
    env_config_src = artifacts_dir / "configs" / f"bijou_{net_profile}.json"
    env_config_dst = target_configs / "runtime_config.json"

    if env_config_src.exists() and not env_config_dst.exists():
        shutil.copy2(env_config_src, env_config_dst)
        log(f"Applied network profile '{net_profile}' from {env_config_src}")
    elif not env_config_dst.exists():
        default_cfg = {
            "profile": net_profile,
            "port": int(port),
            "aurarouter": {
                "enabled": False,
                "endpoint": os.environ.get("AURAROUTER_URL", "http://127.0.0.1:9090"),
                "auto_extract": True,
            },
        }
        env_config_dst.write_text(json.dumps(default_cfg, indent=2), encoding="utf-8")
        log(f"Generated default runtime configuration at {env_config_dst}")

    # 4. Sister / Integration Dependency Check: AuraRouter
    check_cmd = [str(python_exe), "-c", "import aurarouter; print(aurarouter.__version__)"]
    res = subprocess.run(check_cmd, capture_output=True, text=True, shell=False)
    if res.returncode == 0:
        log(f"AuraRouter detected: version {res.stdout.strip()}")
    else:
        log("AuraRouter not currently installed.")
        wheels_dir = artifacts_dir / "wheels"
        bundled_wheel = next(wheels_dir.glob("aurarouter-*.whl"), None) if wheels_dir.exists() else None
        if bundled_wheel and bundled_wheel.exists():
            log(f"Found bundled AuraRouter wheel at {bundled_wheel}. Installing...")
            pip_res = subprocess.run(
                [str(python_exe), "-m", "pip", "install", str(bundled_wheel)],
                capture_output=True,
                text=True,
                shell=False,
            )
            if pip_res.returncode == 0:
                log("Successfully installed bundled AuraRouter.")
            else:
                log(f"Warning: Failed to install bundled AuraRouter: {pip_res.stderr}")
        else:
            log("No local AuraRouter wheel found in artifacts/wheels (stand-alone mode).")

    # 5. Generate Installation Receipt for Auditing / Provenance
    receipt_file = install_dir / "install_receipt.json"
    receipt_data = {
        "app_id": app_id,
        "version": version,
        "installer": "aurasprout" if os.environ.get("AURASPROUT_INSTALL_DIR") else "auraseed",
        "install_dir": str(install_dir),
        "python_exe": str(python_exe),
        "port": int(port),
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt_file.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")
    log("Installation receipt recorded successfully.")
    log("=" * 60)


if __name__ == "__main__":
    main()
