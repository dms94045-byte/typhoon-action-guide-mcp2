from typhoon_mcp.region import find_region, infer_environment, infer_intent

def test_region_find():
    assert find_region("제주 서귀포야") is not None
    assert find_region("부산인데") is not None

def test_env():
    assert infer_environment("해안 근처야") == "해안·섬"
    assert infer_environment("하천 근처 저지대") == "저지대·하천"

def test_intent():
    assert infer_intent("몇 시가 제일 위험해?") == "위험시간"
    assert infer_intent("지금 나가도 돼?") == "외출가능"
