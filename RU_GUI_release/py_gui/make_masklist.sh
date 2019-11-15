#!/bin/bash
#format is connector,chipid,col,row
for i in `seq 0 1023`;do echo "1,8,$i,159";done
for i in `seq 0 1023`;do echo "1,8,$i,127";done
for i in `seq 0 1023`;do echo "1,7,$i,158";done
for i in `seq 0 1023`;do echo "1,6,$i,159";done
for i in `seq 0 1023`;do echo "1,3,$i,161";done
for i in `seq 0 1023`;do echo "1,3,$i,163";done
for i in `seq 0 1023`;do echo "1,0,$i,162";done
