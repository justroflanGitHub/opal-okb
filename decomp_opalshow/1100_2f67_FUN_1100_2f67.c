
void __cdecl16near FUN_1100_2f67(void)

{
  byte *pbVar1;
  int *piVar2;
  byte bVar3;
  undefined2 uVar4;
  undefined2 uVar5;
  char cVar6;
  undefined2 uVar7;
  undefined2 in_BX;
  int iVar8;
  int unaff_SI;
  undefined2 unaff_DI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar9;
  
  uVar4 = *(undefined2 *)0x1120;
  uVar5 = *(undefined2 *)0x111e;
  *(undefined2 *)0x116c = unaff_DI;
  uVar7 = FUN_1100_2cf1();
  bVar9 = (char)uVar7 == '\0';
  if ((bVar9) || (uVar7 = FUN_1100_30a7(), bVar9)) {
    iVar8 = *(int *)0x116c;
    while (iVar8 != 0) {
      unaff_SI = unaff_SI + 1;
      *(int *)0x1120 = unaff_SI;
      *(undefined1 *)0x111e = 0x80;
      iVar8 = 0;
      do {
        if (((*(byte *)0x111e & (byte)((uint)uVar7 >> 8)) != 0) &&
           (cVar6 = (*(code *)*(undefined2 *)0x31a)(), cVar6 != *(char *)(iVar8 + 0x1164)))
        goto LAB_1100_2fc8;
        iVar8 = iVar8 + 1;
        pbVar1 = (byte *)0x111e;
        bVar3 = *pbVar1;
        *pbVar1 = *pbVar1 >> 1;
      } while (!(bool)(bVar3 & 1));
      piVar2 = (int *)0x116c;
      *piVar2 = *piVar2 + -1;
      iVar8 = *piVar2;
    }
    if ((char)((uint)in_BX >> 8) != '\0') {
      FUN_1100_3073(in_BX);
    }
  }
LAB_1100_2fc8:
  *(undefined2 *)0x111e = uVar5;
  *(undefined2 *)0x1120 = uVar4;
  return;
}

