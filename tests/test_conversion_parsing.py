from panid.panid import Conversion, IdType

conversion_tests = [
    (
        "ensg:ensg+ensgv:ensg_version",
        Conversion(
            "ensg", 
            IdType.ENSG,
            "ensgv",
            IdType.ENSG_VERSION,
            True
        )
    ),
    (
        "banana:ensg_version>papayalama wow!:ensg",
        Conversion(
            "banana",
            IdType.ENSG_VERSION,
            "papayalama wow!",
            IdType.ENSG,
            False
        )
    )
]

def test_conversion_parsing():
    for string, conversion in conversion_tests:
        print(f"Testing {string}")
        assert Conversion.from_string(string) == conversion

