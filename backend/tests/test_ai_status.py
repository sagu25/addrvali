from app.ai.status_check import check_azure_openai_status


def test_status_check_reports_not_configured_without_credentials():
    status = check_azure_openai_status()
    assert status["configured"] is False
    assert status["liveCallOk"] is None
    assert "not configured" in status["liveCallError"].lower()
