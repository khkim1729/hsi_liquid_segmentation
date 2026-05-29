# Living Optics `liquid-segmentation.lo` 데이터 분석 정리

## 1. 결론 요약

`liquid-segmentation.lo` 파일은 **Living Optics 초분광 카메라에서 생성된 전용 `.lo` 포맷 데이터**로 보이며, 분석은 가능합니다. 다만 `.lo`는 일반적인 ENVI `.hdr/.raw`, `.mat`, `.tif` 같은 공개 표준 포맷이 아니라 **Living Optics 전용 포맷**이므로, 기본적으로는 **Living Optics Analysis Tool 또는 SDK**를 통해 열고 추출해야 합니다.

핵심적으로 보면 다음과 같습니다.

```text
파일명: liquid-segmentation.lo
형식: Living Optics 전용 LOFMT 기반 .lo 파일
성격: 초분광 비디오 / spatial-spectral video recording
크기: 약 2.5GB
분석 가능 여부: 가능
필요 도구: Living Optics Analysis Tool 또는 Living Optics SDK
주의점: proprietary format이므로 일반 Python 라이브러리만으로 바로 열기 어려울 수 있음
```

---

## 2. `.lo` 파일은 무슨 형식인가?

`.lo`는 Living Optics 카메라에서 생성되는 **처리된 hyperspectral video 파일**입니다. 공식 문서 기준으로 `.lo` 확장자는 Living Optics Camera의 **spatial-spectral video recording**이며, 내부적으로는 proprietary format인 **LOFMT**로 저장됩니다.

쉽게 말하면 다음과 같습니다.

> `.lo` = Living Optics 전용 초분광 동영상 파일  
> 한 프레임 안에 RGB처럼 보이는 장면 이미지와, 해당 장면에서 추출된 스펙트럼 샘플들이 함께 들어 있는 구조

일반 이미지 파일처럼 단순히 한 장의 이미지가 들어 있는 것이 아니라, 여러 프레임과 각 프레임의 스펙트럼 데이터가 함께 들어 있는 **초분광 비디오 데이터**에 가깝습니다.

참고 자료:

- Living Optics Developer Docs - Data Formats  
  https://developer.livingoptics.com/getting-started/dataformats.html
- Living Optics Tutorial - Getting Started with Analysis  
  https://developer.livingoptics.com/tutorials/gs-analysis.html

---

## 3. 데이터 구조는 어떻게 생겼는가?

일반적인 초분광 데이터는 보통 다음과 같은 형태를 가집니다.

```text
image_cube.shape = (Height, Width, Bands)
```

예를 들어 96개 wavelength band를 가진 초분광 이미지라면 다음과 같은 구조로 이해할 수 있습니다.

```text
image_cube.shape = (H, W, 96)
```

다만 Living Optics `.lo` 파일은 일반적인 dense hyperspectral cube와 완전히 동일하게 보기 어렵습니다. 공식 문서에 따르면 Living Optics의 spectral sampling은 **sparse**한 구조입니다. 즉, 모든 픽셀마다 스펙트럼이 빽빽하게 존재하는 전통적인 큐브 방식이라기보다, 장면 위에 분산된 스펙트럼 샘플들이 존재하는 방식으로 이해하는 것이 좋습니다.

단순화하면 다음과 같은 구조입니다.

```text
liquid-segmentation.lo
 ├─ frame 0
 │   ├─ scene image
 │   ├─ spectral samples
 │   └─ metadata
 ├─ frame 1
 │   ├─ scene image
 │   ├─ spectral samples
 │   └─ metadata
 ├─ frame 2
 │   └─ ...
```

따라서 이 파일은 단일 초분광 이미지라기보다는 **프레임 단위로 저장된 초분광 비디오 파일**로 보는 것이 적절합니다.

---

## 4. 2.5GB인 이유

`liquid-segmentation.lo` 파일의 크기가 약 **2.5GB**인 것은 초분광 데이터 특성상 이상한 크기는 아닙니다.

RGB 영상은 보통 3개 채널만 다루지만, 초분광 영상은 수십 개에서 수백 개의 wavelength band를 다룹니다. 여기에 프레임이 여러 장 포함된 비디오 형태라면 파일 크기는 쉽게 GB 단위가 됩니다.

Living Optics 개발 키트 관련 자료에서는 VIS-NIR 영역에서 대략 **440–900nm**, **96개 wavelength bands**, **30fps** 수준의 video-rate spectral imaging을 지원하는 것으로 소개됩니다. 따라서 2.5GB 크기의 `.lo` 파일은 여러 프레임이 포함된 액체 분할/분류 실험 데이터일 가능성이 있습니다.

참고 자료:

- Living Optics Development Kit 자료  
  https://www.ieee-whispers.com/wp-content/uploads/2024/12/pbf-lodevkit-LIVING-OPTICS.pdf

---

## 5. `liquid-segmentation.lo`에서 가능한 분석

파일명이 `liquid-segmentation.lo`인 점을 고려하면, 액체 분류 또는 액체 영역 분할 실험용 데이터일 가능성이 높습니다. Living Optics는 hyperspectral data를 이용해 서로 다른 fluid type을 구분하고 segment/track하는 예시를 소개하고 있습니다.

가능한 분석 항목은 다음과 같습니다.

| 분석 항목 | 가능 여부 | 설명 |
|---|---:|---|
| 프레임별 장면 이미지 확인 | 가능 | `.lo` 파일을 재생하면서 scene view 확인 |
| 특정 ROI 스펙트럼 추출 | 가능 | 컵, 액체, 배경 등 영역별 평균 스펙트럼 비교 |
| 액체 종류 분류 | 가능 | 물, 기름, 색소, 기타 액체의 spectral signature 비교 |
| 액체 segmentation | 가능 | 특정 spectrum과 유사한 영역을 분할 |
| frame 단위 변화 분석 | 가능 | 시간에 따른 액체 위치, 혼합, 이동 분석 |
| ML 학습용 데이터셋 변환 | 가능 | annotation, spectrum, label 형태로 export 후 학습 가능 |

참고 자료:

- Living Optics - Real-time recognition and segmentation through HSI camera  
  https://www.livingoptics.com/real-time-recognition-and-segmentation-through-living-optics-hsi-camera/
- Living Optics Software  
  https://www.livingoptics.com/living-optics-software/

---

## 6. 분석에 필요한 도구

### 6.1 1순위: Living Optics Analysis Tool

가장 현실적인 방법은 **Living Optics Analysis Tool**을 사용하는 것입니다. Living Optics 다운로드 페이지에 따르면 Analysis Tool은 `.lo` 파일을 직접 지원하며, Headwall, Resonon, Specim ENVI 파일과 CSV point spectrometer 데이터도 지원한다고 설명되어 있습니다.

권장 흐름은 다음과 같습니다.

```text
Living Optics Analysis Tool 설치
→ liquid-segmentation.lo 열기
→ 프레임 확인
→ Decode Spectra 실행
→ ROI별 spectrum 추출
→ 필요 시 export
```

공식 튜토리얼에서는 다음과 같이 실행하는 예시가 나옵니다.

```bash
analysis-qt --file /path/to/file.lo
```

이후 UI에서 `Decode Spectra` 버튼을 누르고 spectral segmentation routine을 선택하는 흐름입니다.

참고 자료:

- Living Optics Downloads  
  https://www.livingoptics.com/downloads/
- Living Optics Tutorial - Getting Started with Analysis  
  https://developer.livingoptics.com/tutorials/gs-analysis.html

---

### 6.2 2순위: Living Optics SDK / Python API

Living Optics는 Python 예제와 SDK를 제공합니다. GitHub의 `datareader` 예제는 exported dataset을 읽고, annotation, spectra, metadata, calibration spectra 등에 접근하는 구조를 보여줍니다.

다만 `.lo` 원본 파일을 Python에서 자유롭게 직접 파싱하는 공개 코드가 완전히 열려 있는 형태는 아닌 것으로 보입니다. 공식 문서에서도 자세한 data format 정보는 SDK API Reference를 보라고 안내하고 있으며, 일부 기능은 Basic tier 이상 접근이 필요할 수 있습니다.

참고 자료:

- Living Optics datareader GitHub  
  https://github.com/livingoptics/datareader
- Living Optics Developer Docs - Data Formats  
  https://developer.livingoptics.com/getting-started/dataformats.html

---

## 7. 현재 파일만으로 바로 가능한 것과 어려운 것

현재 확인 가능한 것은 파일 목록 스크린샷 기준 정보입니다. 실제 `.lo` 파일 자체가 제공된 것은 아니므로 내부의 정확한 frame 수, wavelength range, band 수, metadata, scene size, spectral sample 수는 직접 확인할 수 없습니다.

따라서 현재 단계에서 말할 수 있는 것은 다음과 같습니다.

```text
가능한 판단:
- Living Optics 전용 .lo 파일로 보임
- 초분광 비디오 데이터일 가능성이 높음
- 액체 segmentation 실험 데이터일 가능성이 높음
- Analysis Tool 또는 SDK를 통해 분석 가능

아직 확인 불가능한 정보:
- 총 frame 수
- 정확한 wavelength range
- band 수
- FPS
- scene image 해상도
- spectral sample 구조
- export 가능한 실제 데이터 형식
```

---

## 8. 추천 분석 진행 순서

실제 분석은 아래 순서로 진행하는 것이 가장 안전합니다.

```text
1. Living Optics Analysis Tool 설치
2. liquid-segmentation.lo 파일 열기
3. 프레임 수, wavelength range, band 수, FPS 확인
4. Decode Spectra 실행
5. 액체 영역과 배경 영역 ROI 선택
6. ROI별 평균 spectrum 비교
7. segmentation 결과 확인
8. export 가능한 형식 확인
   - CSV
   - annotation dataset
   - frame image
   - spectrum data
   - 가능하다면 ENVI 또는 NumPy 변환
9. 이후 Python에서 분류/분할 모델 학습
```

---

## 9. Python 분석으로 넘어가기 위한 목표 데이터 형태

Living Optics Tool에서 export가 가능하다면, 최종적으로는 다음과 같은 형태로 변환하는 것이 좋습니다.

### 9.1 스펙트럼 분류용 CSV

```text
sample_id, frame_id, x, y, wavelength_1, wavelength_2, ..., wavelength_n, label
```

예시:

```text
0001, 0, 120, 88, 0.13, 0.18, ..., 0.42, water
0002, 0, 150, 92, 0.11, 0.17, ..., 0.39, oil
```

이 구조는 Random Forest, SVM, XGBoost, MLP 같은 모델 학습에 적합합니다.

### 9.2 segmentation 학습용 데이터

```text
frame image
+ spectral features
+ mask label
```

예시 구조:

```text
dataset/
 ├─ images/
 │   ├─ frame_0001.png
 │   ├─ frame_0002.png
 ├─ spectra/
 │   ├─ frame_0001.npy
 │   ├─ frame_0002.npy
 ├─ masks/
 │   ├─ frame_0001_mask.png
 │   ├─ frame_0002_mask.png
```

이 구조는 U-Net, DeepLab, SegFormer, SAM 기반 후처리 등으로 확장하기 좋습니다.

---

## 10. 최종 정리

`liquid-segmentation.lo`는 Living Optics 카메라의 **전용 초분광 비디오 파일**로 보는 것이 가장 타당합니다. 내부에는 장면 이미지, 스펙트럼 샘플, 프레임 메타데이터가 함께 들어 있을 가능성이 높습니다.

일반적인 `.mat`, `.tif`, `.hdr`처럼 바로 열리는 공개 포맷은 아니므로, **Living Optics Analysis Tool 또는 SDK를 통해 열고 export하는 방식**이 현실적입니다.

파일명상 액체 분할/분류용 예제 데이터일 가능성이 높고, 분석 방향은 다음과 같습니다.

```text
1. 프레임 확인
2. 스펙트럼 디코딩
3. 액체/배경 ROI 설정
4. 평균 스펙트럼 비교
5. segmentation 결과 확인
6. CSV 또는 학습 데이터셋으로 export
7. Python 기반 분류/분할 모델 학습
```

즉, 이 데이터는 충분히 분석 가능하지만, 첫 단계는 Python 코드 작성이 아니라 **Living Optics 전용 툴에서 파일을 정상적으로 열고 export 가능한지 확인하는 것**입니다.
