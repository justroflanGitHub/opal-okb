
void __cdecl16near FUN_1100_2dd2(void)

{
  undefined1 *puVar1;
  undefined1 uVar2;
  char cVar3;
  byte bVar4;
  undefined1 extraout_AH;
  char extraout_AH_00;
  undefined2 in_CX;
  char cVar5;
  int iVar6;
  int extraout_DX;
  int extraout_DX_00;
  int extraout_DX_01;
  undefined2 in_BX;
  int unaff_BP;
  undefined1 *unaff_SI;
  undefined1 *unaff_DI;
  undefined1 *puVar7;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
  cVar5 = (char)((uint)in_CX >> 8);
  bVar4 = *(byte *)0x2e8;
  if (*(char *)0x1125 != '\0') {
    bVar4 = bVar4 & 0x10;
  }
  out(0x3ce,5);
  out(0x3cf,bVar4);
  iVar6 = 0x3ce;
  out(0x3ce,8);
  uVar2 = (undefined1)in_BX;
  if (*(char *)0x1125 != '\0') {
    FUN_1100_2cf1();
    uVar2 = extraout_AH;
    iVar6 = extraout_DX;
  }
  out(iVar6 + 1,uVar2);
  if (*(char *)0x1125 == '\0') {
    in_BX = CONCAT11((char)((uint)in_BX >> 8),*(undefined1 *)0x111f);
    *unaff_DI = *(undefined1 *)0x111f;
  }
  else {
    FUN_1100_2e8d();
    iVar6 = extraout_DX_00;
  }
  cVar3 = (char)((uint)in_BX >> 8);
  if (cVar3 == '\0') {
    FUN_1100_2ef5();
    uVar2 = (undefined1)in_BX;
  }
  else {
    out(iVar6,8);
    if (*(char *)0x1125 != '\0') {
      FUN_1100_2cf1();
      cVar3 = extraout_AH_00;
      iVar6 = extraout_DX_01;
    }
    uVar2 = (undefined1)in_BX;
    out(iVar6 + 1,cVar3);
    if (*(char *)0x1125 == '\0') {
      *unaff_SI = uVar2;
    }
    else {
      FUN_1100_2e8d();
    }
    FUN_1100_2ef5();
  }
  if (unaff_BP != 0) {
    puVar7 = unaff_DI + 1;
    if (cVar5 != '\0') {
      puVar7 = unaff_DI + -1;
    }
    if (*(char *)0x1125 == '\0') {
      for (; unaff_BP != 0; unaff_BP = unaff_BP + -1) {
        puVar1 = puVar7;
        puVar7 = puVar7 + 1;
        *puVar1 = uVar2;
      }
    }
    else {
      FUN_1100_2cf1();
      FUN_1100_10cc();
      do {
        FUN_1100_2e8d();
        unaff_BP = unaff_BP + -1;
      } while (unaff_BP != 0);
    }
  }
  return;
}

