
void FUN_0100_18ad(void)

{
  code *pcVar1;
  undefined2 uVar2;
  byte bVar3;
  int iVar4;
  int iVar5;
  byte *pbVar6;
  byte *pbVar7;
  undefined2 unaff_CS;
  undefined2 unaff_DS;
  undefined1 in_CF;
  
  pcVar1 = (code *)swi(0x21);
  (*pcVar1)();
  uVar2 = FUN_0100_1800();
  if (!(bool)in_CF) {
    *(undefined2 *)0x141 = uVar2;
    FUN_0100_1751();
    FUN_0100_17d6();
    FUN_0100_1751();
    iVar5 = *(int *)0x629;
    do {
      pbVar6 = (byte *)(iVar5 + -1);
      FUN_0100_17d6();
      bVar3 = *pbVar6;
      *pbVar6 = bVar3;
      iVar4 = 0x5f;
      pbVar7 = pbVar6;
      do {
        pbVar7 = pbVar7 + 1;
        pbVar6 = pbVar6 + 1;
        *pbVar7 = (((*pbVar6 ^ bVar3) >> (bVar3 & 7) | (*pbVar6 ^ bVar3) << 8 - (bVar3 & 7)) ^ 0x5a)
                  - (bVar3 ^ 0x53) ^ 0xc5;
        bVar3 = bVar3 - 7;
        iVar4 = iVar4 + -1;
      } while (iVar4 != 0);
      iVar5 = iVar5 + -1;
    } while (iVar5 != 0);
  }
  return;
}

