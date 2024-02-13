def pytest_addoption(parser):
    parser.addoption('--longrun', action='store_true', dest="longrun",
                 default=False, help="run slow tests")

