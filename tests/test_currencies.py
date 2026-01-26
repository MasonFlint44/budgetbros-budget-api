async def test_list_currencies(async_client, seeded_currencies) -> None:
    response = await async_client.get("/currencies")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2

    codes = {currency["code"] for currency in payload}
    assert codes == {"USD", "EUR"}

    by_code = {currency["code"]: currency for currency in payload}
    assert by_code["USD"]["name"] == "US Dollar"
    assert by_code["USD"]["symbol"] == "$"
    assert by_code["USD"]["minor_unit"] == 2
    assert by_code["EUR"]["name"] == "Euro"
    assert by_code["EUR"]["symbol"] == "EUR"
    assert by_code["EUR"]["minor_unit"] == 2


async def test_list_currencies_empty(async_client) -> None:
    response = await async_client.get("/currencies")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
