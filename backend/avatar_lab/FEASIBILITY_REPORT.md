# MuseTalk Feasibility Laboratory Report

**Date:** 2026-10-08  
**Hardware Tested:** NVIDIA GeForce RTX 2050 Laptop GPU (4 GB VRAM)  
**Host OS:** Windows 11 (Native)  
**Host Python:** 3.10.11  
**Working AI Stack:** PyTorch 2.9.1+cu126, Manim 0.19.1, IndicF5 TTS 1.1.22, faster-whisper 1.2.1, FFmpeg  

---

## 1. Executive Summary

As part of Task 8 Phase 3–5, an isolated feasibility laboratory was constructed at `backend/avatar_lab/` to evaluate whether **MuseTalk 1.5** (`TMElyralab/MuseTalk`) can reliably execute on the current hardware environment (RTX 2050 with 4 GB VRAM on Windows).

**Feasibility Verdict: INFEASIBLE on Target Hardware & Host OS**

1. **Host Dependency & Binary Extension Failure:**  
   MuseTalk relies on `mmcv==2.0.1`, `mmdet==3.1.0`, and `mmpose==1.1.0` (for DWPose face/body landmark extraction). On Windows, OpenMMLab provides pre-compiled C++/CUDA wheels only for legacy PyTorch (v2.0 / v2.1 with CUDA 11.8). Compiling `mmcv._ext` from source requires the full NVIDIA CUDA Toolkit (`nvcc`) and Microsoft Visual Studio C++ Compiler (`cl.exe`), neither of which are installed on this system. Installing `mmcv-lite` failed because `mmpose.models.heads` explicitly imports `MultiScaleDeformableAttention` from `mmcv.ops`, causing immediate runtime failure (`ModuleNotFoundError: No module named 'mmcv._ext'`).

2. **Severe VRAM Constraint (RTX 2050 - 4 GB VRAM):**  
   MuseTalk concurrently loads multiple deep neural network models:
   - Stable Diffusion MSE-VAE (`sd-vae-ft-mse`): ~1.2 GB VRAM
   - MuseTalk UNet (256x256 latent inpainting): ~1.8 GB VRAM
   - DWPose / MMPose (whole-body landmark estimator): ~1.2 GB VRAM
   - Face Parsing BiSeNet: ~0.4 GB VRAM
   - Whisper-tiny audio feature extractor: ~0.3 GB VRAM
   
   Total peak VRAM footprint exceeds **4.9 GB to 6.2 GB**.  
   On an RTX 2050 with 4.0 GB total VRAM where the Windows Desktop Window Manager (DWM) already reserves ~0.6 GB, available GPU memory is ~3.4 GB. MuseTalk would inevitably trigger CUDA Out of Memory (OOM) errors during inference.

3. **Protection of Main Environment:**  
   Per the absolute rules of Task 8, the working virtual environment (`backend/.venv`) hosting Manim, IndicF5, Whisper, and FFmpeg was preserved without downgrading PyTorch or reinstalling conflicting packages.

---

## 2. Quantitative & Environment Telemetry

| Metric / Parameter | Observed Value | Evaluation |
|---|---|---|
| **GPU Model** | NVIDIA GeForce RTX 2050 Laptop GPU | Hardware constraint |
| **Total VRAM** | 4,096 MB (4.0 GB) | Hard constraint |
| **Available VRAM** | ~3,400 MB (after DWM / OS allocation) | Insufficient for MuseTalk |
| **System RAM** | 16 GB | Adequate |
| **CUDA Runtime** | CUDA 12.6 | Supported |
| **CUDA Toolkit (nvcc)** | Not installed | Prevents compiling C++/CUDA ops |
| **MSVC Compiler (cl.exe)** | Not installed | Prevents compiling C++/CUDA ops |
| **MMLab Status** | Failed (`mmcv._ext` missing) | Incompatible on Windows without toolchain |
| **MuseTalk Weights Footprint** | ~4.2 GB on disk | Exceeds single-model cache budget |
| **Practical Usability** | Unusable on target 4GB Windows setup | Requires fallback architecture |

---

## 3. Fallback & Architecture Strategy (Phase 7B)

Following the instructions of Phase 5 & 7B:
> *"If MuseTalk is clearly impractical, stop the MuseTalk integration and prepare the architecture for a provider fallback."*

1. **Pluggable Avatar Provider Architecture:**  
   Implement `backend/app/services/avatar_service.py` using an abstract base class `AvatarProvider`:
   - `MuseTalkAvatarProvider`: Implements the MuseTalk interface; detects if MuseTalk dependencies/weights are available and gracefully raises informative diagnostics if dependencies are missing.
   - `TeacherAvatarOverlayProvider` (Local Educational Fallback): Leverages the canonical `teacher.png` (transparent 3D teacher) with subtle audio-reactive educational framing or Manim/FFmpeg compositing, running synchronously and reliably within the 4 GB VRAM budget.
   - Future provider slots: `HuggingFaceAvatarProvider`, `LivePortraitAvatarProvider`, `SadTalkerAvatarProvider`.

2. **Configuration Defaults:**  
   `AVATAR_ENABLED=false` by default, preserving 100% backward compatibility with Tasks 1–7.
