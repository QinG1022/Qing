import pytest
import warnings

@pytest.fixture(autouse=True)
def ignore_reportlab_warnings():
    """自动忽略 ReportLab 的废弃警告"""
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="reportlab.lib.rl_safe_eval"
    )
