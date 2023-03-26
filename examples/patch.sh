python examples/patch.py
python rfems.py examples/patch --pitch .005 --frequency 2e9 --criteria -40 --threads $(nproc) --farfield $@
python examples/showresult.py examples/patch
