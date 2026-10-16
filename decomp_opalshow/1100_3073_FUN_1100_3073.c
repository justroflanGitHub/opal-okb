
void __cdecl16near FUN_1100_3073(void)

{
  char *pcVar1;
  byte bVar2;
  char cVar3;
  undefined2 in_AX;
  byte bVar4;
  int iVar5;
  undefined2 unaff_SI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  bVar4 = 0x80;
  iVar5 = 8;
  do {
    bVar4 = bVar4 << 1 | (char)bVar4 < '\0';
    iVar5 = iVar5 + -1;
    bVar2 = (byte)in_AX;
    in_AX = CONCAT11((char)((uint)in_AX >> 8),bVar2 >> 1 | bVar2 << 7);
  } while (!(bool)(bVar2 & 1));
  *(byte *)0x111e = bVar4;
  while( true ) {
    bVar4 = (byte)((uint)in_AX >> 8);
    if ((*(byte *)0x111e & bVar4) != 0) {
      *(undefined2 *)0x1120 = unaff_SI;
      cVar3 = (*(code *)*(undefined2 *)0x31a)();
      if (*(char *)(iVar5 + 0x1164) != cVar3) {
        return;
      }
    }
    iVar5 = iVar5 + -1;
    bVar2 = (byte)in_AX;
    in_AX = CONCAT11(bVar4,bVar2 >> 1 | bVar2 << 7);
    if (!(bool)(bVar2 & 1)) break;
    pcVar1 = (char *)0x111e;
    cVar3 = *pcVar1;
    *pcVar1 = *pcVar1 << 1;
    if (cVar3 < '\0') {
      return;
    }
  }
  return;
}

