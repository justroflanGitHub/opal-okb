
void FUN_0000_28e8(void)

{
  byte bVar1;
  int in_CX;
  int iVar2;
  byte *pbVar3;
  byte *pbVar4;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
  do {
    pbVar3 = (byte *)(in_CX + -1);
    FUN_0100_17d6();
    bVar1 = *pbVar3;
    *pbVar3 = bVar1;
    iVar2 = 0x5f;
    pbVar4 = pbVar3;
    do {
      pbVar4 = pbVar4 + 1;
      pbVar3 = pbVar3 + 1;
      *pbVar4 = (((*pbVar3 ^ bVar1) >> (bVar1 & 7) | (*pbVar3 ^ bVar1) << 8 - (bVar1 & 7)) ^ 0x5a) -
                (bVar1 ^ 0x53) ^ 0xc5;
      bVar1 = bVar1 - 7;
      iVar2 = iVar2 + -1;
    } while (iVar2 != 0);
    in_CX = in_CX + -1;
  } while (in_CX != 0);
  return;
}

