
void __cdecl16near FUN_1100_30a7(void)

{
  byte *pbVar1;
  char cVar2;
  undefined2 in_AX;
  byte bVar3;
  int iVar4;
  undefined2 unaff_SI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  bVar3 = 1;
  iVar4 = -1;
  do {
    bVar3 = bVar3 >> 1 | bVar3 << 7;
    iVar4 = iVar4 + 1;
    cVar2 = (char)in_AX;
    in_AX = CONCAT11((char)((uint)in_AX >> 8),cVar2 << 1 | cVar2 < '\0');
  } while (cVar2 >= '\0');
  *(undefined2 *)0x1120 = unaff_SI;
  *(byte *)0x111e = bVar3;
  do {
    bVar3 = (byte)((uint)in_AX >> 8);
    if (((*(byte *)0x111e & bVar3) != 0) &&
       (cVar2 = (*(code *)*(undefined2 *)0x31a)(), *(char *)(iVar4 + 0x1164) != cVar2)) {
      return;
    }
    cVar2 = (char)in_AX;
    in_AX = CONCAT11(bVar3,cVar2 << 1 | cVar2 < '\0');
    if (cVar2 >= '\0') {
      return;
    }
    iVar4 = iVar4 + 1;
    pbVar1 = (byte *)0x111e;
    bVar3 = *pbVar1;
    *pbVar1 = *pbVar1 >> 1;
  } while (!(bool)(bVar3 & 1));
  return;
}

