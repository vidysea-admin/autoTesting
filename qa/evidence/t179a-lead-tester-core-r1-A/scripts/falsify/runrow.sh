#!/bin/bash
# runrow.sh n file node old new
R=C:/Users/Lenovo/AppData/Local/Temp/chkA_t179r1_355800; H=$R/head; E=$R/evidence/falsify
cd $R/scripts/falsify
n=$1; file=$2; node=$3; old=$4; new=$5; C=$R/scripts/falsify/row$n$SUF; out=$E/row$n$SUF.log; [ -n "$8" ] && { C=$R/scripts/falsify/row$n$SUF; }
cp $H/$file $C/$file
echo "== (a) BEFORE edit (expect green)" > $out
TAILN=12 ./probe.sh $C $node >> $out 2>&1
$H/.venv/Scripts/python mutate.py $C/$file "$old" "$new" >> $out 2>&1 || echo "MUTATION FAILED" >> $out
[ -n "$6" ] && $H/.venv/Scripts/python mutate.py $C/$file "$6" "$7" >> $out 2>&1
diff -u $H/$file $C/$file | sed "s#$R/##g" > $E/row$n$SUF.diff
echo "== (c) AFTER edit (expect red on intended assertion)" >> $out
TAILN=70 ./probe.sh $C $node >> $out 2>&1
cp $H/$file $C/$file
echo "== (d) RESTORED (expect green); cmp:" >> $out
cmp $H/$file $C/$file && echo identical-to-HEAD >> $out
TAILN=12 ./probe.sh $C $node >> $out 2>&1
echo DONE >> $out
