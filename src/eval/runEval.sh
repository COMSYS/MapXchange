#!/usr/bin/env bash

#echo "Paillier"
#time python3 -m src.eval.paillier -o paillier


#echo "Reverse query, w/ Paillier w/ TLS w/o RAM, no validation"
#time python3 -m src.eval.reverse_query -o reverse_r_invalid -r --invalid

#echo "Regular query, 1 value stored, w/ Paillier w/ TLS w/o RAM, no validation"
#time python3 -m src.eval.regular_query -o regular_1_r_invalid -s 1 -r --invalid

#echo "Provision, 0 values stored, w/ Paillier w/ TLS w/o RAM, no validation"
#time python3 -m src.eval.provision -o provision_0_r_invalid -s 0 -r --invalid

#echo "Provision, 1 value stored, w/ Paillier w/ TLS w/o RAM, no validation"
#time python3 -m src.eval.provision -o provision_1_r_invalid -s 1 -r --invalid


#echo "Regular query, 1 value stored, w/ Paillier w/ TLS w/o RAM, no validation, real-world data"
#time python3 -m src.eval.regular_query -o regular_1_r_invalid_real -s 1 -r --invalid --real

#echo "Provision, 0 values stored, w/ Paillier w/ TLS w/o RAM, no validation, real-world data"
#time python3 -m src.eval.provision -o provision_0_r_invalid_real -s 0 -r --invalid --real

#echo "Provision, 1 value stored, w/ Paillier w/ TLS w/o RAM, no validation, real-world data"
#time python3 -m src.eval.provision -o provision_1_r_invalid_real -s 1 -r --invalid --real


#echo "Provision, 3 values stored, w/ Paillier w/ TLS w/o RAM"
#time python3 -m src.eval.provision -o provision_3_r -s 3 -r
