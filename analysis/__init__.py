"""Analysis layer — ray tracing, aberrations, diffraction, Zernike, advanced analysis.

Modules:
    ray_tracing:  Real ray tracing through spherical/aspheric surfaces.
    aberrations:  Transverse, longitudinal, wavefront aberrations, spot diagrams.
    advanced:     PSF, LSF, ENC, PTF via FFT of pupil function.
    zernike:      Zernike polynomial decomposition of wavefront.
    diffraction:  Diffraction MTF via FFT.
    tables:       OPAL-таблицы TABGL/TABPR2 (реверс §15).
    vignetting:   Виньетирование, светораспределение, TABBEA (реверс §14/§17.6).
    strehl:       Число Штреля: Марешаль + точный FFT-PSF.
    psf_mtf:      ФРТ/ФРЛ/ОПФ/ФКЭ и миры — уровень-2 анализа (DIA, §9).
"""
