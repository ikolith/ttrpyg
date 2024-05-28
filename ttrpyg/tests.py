import pytest
from ttrpyg.database import DB
import ttrpyg.text as tx


@pytest.fixture
def test_db(tmp_path):
    # Specify paths for input and output JSON files
    input_path = "./source"
    output_path = str(
        tmp_path / "test_db.json"
    )  # Use the tmp_path for the test database

    # Call create_tinydb with the specified input and output paths
    db = DB()

    yield db  # Yield the database object to the tests
    db.close()  # Close the database when the tests are


# not sure we need an outside of funcs db
db = DB()  # dt.create_tinydb()


def test_parse_curlies():
    test_str = """
test test test
{1d1+3 T e ' s t ! 2d1-1}
{1 ()()TEST()() 2}
test test test {4d1}
"""
    result = [
        {
            "match": "{1d1+3 T e ' s t ! 2d1-1}",
            "quantity_dice": "1d1+3",
            "table_dice": "2d1-1",
            "entity": "t_e__s_t",
            "quantity": 4,
            "table_result": 1,
        },
        {
            "match": "{1 ()()TEST()() 2}",
            "quantity_dice": "",
            "table_dice": "",
            "entity": "test",
            "quantity": 1,
            "table_result": 2,
        },
        {
            "match": "{4d1}",
            "quantity_dice": "4d1",
            "table_dice": "",
            "entity": "",
            "quantity": 4,
            "table_result": None,
        },
    ]
    print(tx.parse_curlies(test_str))
    assert tx.parse_curlies(test_str) == result


def test_fetch_by_name(test_db):
    # remake asserts later
    db.single_curly_parser("{Man From Saint Ives}", False, False).strip()
    db.single_curly_parser("{Man From Saint Ives}", True, False)
