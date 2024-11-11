import pytest

def test_gen_random():
    import os
    return os.urandom(16)

# 복호화 된 Response -> 인가 코드 발급 로직에 전달
async def send_enr_response(response):
        response = test_gen_random()[:15]
        print(f"복호화 된 Response: {response}")
        return await response.decode('utf-8')

# 복호화 된 UUID -> 로그인 처리 로직에 전달
async def send_enr_uuid(uuid):
    uuid = test_gen_random()[16:31]
    print(f"복호화 된 UUID: {uuid}")
    return await uuid.decode('utf-8')

@pytest.mark.asyncio
async def test_send_enr_response(capfd):
    random_value = test_gen_random()
    response = await send_enr_response(random_value)
    uuid = await send_enr_uuid(random_value)

    # 생성된 값 출력
    print(f"Random Value: {random_value}")
    print(f"Response: {response}")
    print(f"UUID: {uuid}")

    # assert 문으로 값 검증
    assert response is not None, "Response should not be None"
    assert uuid is not None, "UUID should not be None"

    # 추가적인 검증
    assert isinstance(response, int), "Response should be a dictionary"
    assert isinstance(uuid, int), "UUID should be a string"

    # 필요에 따라 response의 특정 속성도 확인할 수 있습니다.
    assert 'status' in response, "Response should contain 'status' key"

    # capfd를 사용하여 출력된 내용을 확인할 수 있습니다.
    captured = capfd.readouterr()
    assert f"Random Value: {random_value}" in captured.out
    assert f"Response: {response}" in captured.out
    assert f"UUID: {uuid}" in captured.out
