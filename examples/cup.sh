python examples/cup.py
python rfems.py examples/cup --pitch .005 --frequency 1.3e9 --threads $(nproc) --farfield
python examples/showresult.py examples/cup
