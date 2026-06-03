"""
Retry helper dengan exponential backoff untuk kegagalan jaringan sementara
(CrossRef API, Qdrant Cloud). Menjaga proses ingestion tetap tahan terhadap
gangguan koneksi singkat tanpa menggagalkan keseluruhan batch.
"""

import time
import logging

logger = logging.getLogger(__name__)


def retry_call(
    func,
    *,
    retries: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    label: str = "operation",
):
    """Jalankan ``func()`` dengan retry dan exponential backoff.

    Mengembalikan hasil ``func()`` saat berhasil. Melempar ulang exception
    terakhir jika semua percobaan gagal. Hanya exception pada ``exceptions``
    yang memicu retry.
    """
    delay = base_delay
    for attempt in range(1, retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt >= retries:
                logger.warning(f"{label} gagal setelah {retries} percobaan: {e}")
                raise
            logger.warning(
                f"{label} percobaan {attempt}/{retries} gagal: {e}. "
                f"Mencoba lagi dalam {delay:.1f}s..."
            )
            time.sleep(delay)
            delay *= backoff
