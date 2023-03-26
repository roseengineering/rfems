
python examples/inter.py \
    --rod 0.0006875 -0.001875 0.0006875 \
    --sep 0.0008125 0.0008125 \
    --tap 0.00492334 0.00492334 \
    --qe1 11.7818 11.7818 \
    --kij 0.0600168 0.0600168 \
    --freq 1.296e+09 --a 1 --b 3
python rfems.py examples/inter --freq 1.296e+09 --span 4.4e+08 --line 50 --threads 6 --pitch 0.001 $@
python examples/showresult.py examples/inter
