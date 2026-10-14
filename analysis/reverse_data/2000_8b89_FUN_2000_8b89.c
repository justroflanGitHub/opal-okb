
/* WARNING: Instruction at (ram,0x00028b8a) overlaps instruction at (ram,0x00028b89)
    */

void __stdcall16far FUN_2000_8b89(void)

{
  int *piVar1;
  char *pcVar2;
  undefined2 *puVar3;
  byte bVar4;
  undefined2 uVar5;
  undefined2 *puVar6;
  undefined2 in_AX;
  uint uVar7;
  int iVar8;
  int in_CX;
  int unaff_BP;
  int iVar9;
  undefined2 *puVar10;
  int unaff_DI;
  undefined2 *puVar11;
  undefined2 uVar12;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar13;
  long lVar14;
  
  uVar12 = 0x1000;
  while( true ) {
    unaff_BP = unaff_BP + in_CX;
    pcVar2 = (char *)(unaff_BP + unaff_DI + 0xa46);
    *pcVar2 = *pcVar2 + (char)in_CX;
    bVar13 = (int)(char)in_AX + *(int *)(unaff_BP + -0xc) == 1;
    FUN_3000_1fe6(uVar12,1,0x5ac);
    if (!bVar13) {
      iVar8 = *(int *)(unaff_BP + -0xc);
      uVar12 = (undefined2)((ulong)*(undefined4 *)(unaff_BP + 10) >> 0x10);
      iVar9 = (int)*(undefined4 *)(unaff_BP + 10);
      bVar4 = *(byte *)(iVar8 + iVar9 + -1);
      uVar7 = (uint)bVar4;
      *(uint *)(unaff_BP + -0x2c) = uVar7;
      if ((0x60 < bVar4) && (bVar4 < 0x7b)) {
        *(int *)(unaff_BP + -0x36) = uVar7 - 0x20;
        *(int *)(unaff_BP + -0x34) = -(uint)(uVar7 < 0x20);
        func_0x00032028(0x2e73,1,1,iVar9 + iVar8 + -1,uVar12,1,unaff_BP + -0x36);
      }
      func_0x00032028(0x2e73,1,1,*(int *)(unaff_BP + 10) + *(int *)(unaff_BP + -0xe) + -1,
                      *(undefined2 *)(unaff_BP + 0xc),1,
                      *(int *)(unaff_BP + 10) + *(int *)(unaff_BP + -0xc) + -1,
                      *(undefined2 *)(unaff_BP + 0xc));
      *(int *)(unaff_BP + -0xe) = *(int *)(unaff_BP + -0xe) + 1;
    }
    uVar12 = 0x2e73;
    piVar1 = (int *)(unaff_BP + -0xc);
    iVar8 = *piVar1;
    *piVar1 = *piVar1 + 1;
    if ((SCARRY2(iVar8,1)) || (*(int *)(unaff_BP + -0x38) < *(int *)(unaff_BP + -0xc))) break;
    in_AX = *(undefined2 *)(unaff_BP + 10);
  }
  func_0x00032028(0x2e73,1,(*(int *)(unaff_BP + -0x2a) - *(int *)(unaff_BP + -0xe)) + 1,
                  *(int *)(unaff_BP + 10) + *(int *)(unaff_BP + -0xe) + -1,
                  *(undefined2 *)(unaff_BP + 0xc),1,0x5ab);
  iVar8 = func_0x00032066(0x2e73,0,4,0x5a7);
  *(int *)(unaff_BP + -0xe) = iVar8;
  bVar13 = iVar8 == 0;
  if ((!bVar13) && (FUN_3000_1fe6(0x2e73,1,0x5a6), !bVar13)) {
    piVar1 = (int *)*(undefined4 *)(unaff_BP + 0xe);
    if ((*piVar1 != *(int *)0x5a2) || (((int *)piVar1)[1] != *(int *)0x5a4)) {
      uVar12 = func_0x00032066(0x2e73,0,1,0x5a1);
      *(undefined2 *)(unaff_BP + -0xc) = uVar12;
      func_0x00032028(0x2e73,1,4,*(undefined2 *)(unaff_BP + 0xe),*(undefined2 *)(unaff_BP + 0x10),
                      ((*(int *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -0xc)) -
                      *(int *)(unaff_BP + -0xe)) + -5,
                      *(int *)(unaff_BP + 10) + *(int *)(unaff_BP + -0xe) + 3,
                      *(undefined2 *)(unaff_BP + 0xc));
    }
  }
  lVar14 = func_0x00032066(0x2e73,0,2,0x59f);
  if (lVar14 != 0) {
    puVar6 = (undefined2 *)*(undefined4 *)(unaff_BP + 0x12);
    *puVar6 = 1;
    ((undefined2 *)puVar6)[1] = 0;
  }
  *(undefined2 *)(unaff_BP + -0x28) = *(undefined2 *)0x599;
  *(undefined2 *)(unaff_BP + -0x26) = *(undefined2 *)0x59b;
  *(undefined2 *)(unaff_BP + -0x24) = *(undefined2 *)0x59d;
  *(undefined2 *)(unaff_BP + -0x22) = 0x2020;
  *(undefined2 *)(unaff_BP + -4) = *(undefined2 *)((int)*(undefined4 *)(unaff_BP + -10) + 6);
  *(undefined2 *)(unaff_BP + -2) = 8;
  uVar12 = *(undefined2 *)(unaff_BP + 0xc);
  uVar5 = *(undefined2 *)(unaff_BP + 10);
  *(int *)0x1944 = unaff_BP + -6;
  *(undefined2 *)0x1946 = unaff_SS;
  iVar8 = FUN_2000_8388(uVar5,uVar12,unaff_BP + -0x28);
  *(int *)(unaff_BP + -0xc) = iVar8;
  if (iVar8 != 0) {
    uVar12 = *(undefined2 *)0x3130;
    uVar5 = *(undefined2 *)(unaff_BP + -0x1e);
    *(undefined2 *)0x0 = *(undefined2 *)(unaff_BP + -0x20);
    *(undefined2 *)0x2 = uVar5;
  }
  *(undefined2 *)(unaff_BP + -0x28) = *(undefined2 *)0x593;
  *(undefined2 *)(unaff_BP + -0x26) = *(undefined2 *)0x595;
  *(undefined1 *)(unaff_BP + -0x24) = *(undefined1 *)0x597;
  *(undefined2 *)(unaff_BP + -0x23) = 0x2020;
  *(undefined1 *)(unaff_BP + -0x21) = 0x20;
  *(undefined2 *)(unaff_BP + -4) = *(undefined2 *)((int)*(undefined4 *)(unaff_BP + -10) + 6);
  *(undefined2 *)(unaff_BP + -2) = 8;
  uVar12 = *(undefined2 *)(unaff_BP + 0xc);
  uVar5 = *(undefined2 *)(unaff_BP + 10);
  *(int *)0x1944 = unaff_BP + -6;
  *(undefined2 *)0x1946 = unaff_SS;
  iVar8 = FUN_2000_8388(uVar5,uVar12,unaff_BP + -0x28);
  *(int *)(unaff_BP + -0xc) = iVar8;
  if (((iVar8 != 0) && (*(int *)(unaff_BP + -0x1e) < 1)) &&
     ((*(int *)(unaff_BP + -0x1e) < 0 || (*(uint *)(unaff_BP + -0x20) < 7)))) {
    *(undefined2 *)0x3906 = *(undefined2 *)(unaff_BP + -0x20);
  }
  *(undefined2 *)(unaff_BP + -0x28) = *(undefined2 *)0x58d;
  *(undefined2 *)(unaff_BP + -0x26) = *(undefined2 *)0x58f;
  *(undefined1 *)(unaff_BP + -0x24) = *(undefined1 *)0x591;
  *(undefined2 *)(unaff_BP + -0x23) = 0x2020;
  *(undefined1 *)(unaff_BP + -0x21) = 0x20;
  *(undefined2 *)(unaff_BP + -4) = *(undefined2 *)((int)*(undefined4 *)(unaff_BP + -10) + 6);
  *(undefined2 *)(unaff_BP + -2) = 8;
  uVar12 = *(undefined2 *)(unaff_BP + 0xc);
  uVar5 = *(undefined2 *)(unaff_BP + 10);
  *(int *)0x1944 = unaff_BP + -6;
  *(undefined2 *)0x1946 = unaff_SS;
  iVar8 = FUN_2000_8388(uVar5,uVar12,unaff_BP + -0x28);
  *(int *)(unaff_BP + -0xc) = iVar8;
  if (((iVar8 != 0) && (*(int *)(unaff_BP + -0x1e) < 1)) &&
     ((*(int *)(unaff_BP + -0x1e) < 0 || (*(uint *)(unaff_BP + -0x20) < 7)))) {
    *(undefined2 *)0x3904 = *(undefined2 *)(unaff_BP + -0x20);
  }
  func_0x00032028(0x2e73,1,0x51 - *(int *)0x52,*(int *)0x52 + 0x53,0x54cc,0xc,0x580);
  iVar8 = FUN_3000_0458(0x2e73,0x5ea,0x54,0x54cc);
  *(int *)(unaff_BP + -0x12) = iVar8;
  *(int *)(unaff_BP + -0x10) = iVar8 >> 0xf;
  if (iVar8 == 0) {
    *(undefined2 *)(unaff_BP + -0x36) = 0xd;
    *(undefined2 *)(unaff_BP + -0x34) = 0;
    FUN_2000_cf0b(unaff_BP + -0x36,unaff_SS);
  }
  *(undefined2 *)(unaff_BP + -0x36) = 2;
  *(undefined2 *)(unaff_BP + -0x34) = 0;
  iVar8 = func_0x0002e5a4(0x2e73,0,0x4e0d,unaff_BP + -0x36);
  *(int *)(unaff_BP + -0x2c) = iVar8;
  if (iVar8 == 0) {
    uVar12 = *(undefined2 *)0x312c;
    puVar11 = (undefined2 *)0x8;
    puVar10 = (undefined2 *)0x8;
    for (iVar8 = 0x10; iVar8 != 0; iVar8 = iVar8 + -1) {
      puVar3 = puVar11;
      puVar11 = puVar11 + 1;
      puVar6 = puVar10;
      puVar10 = puVar10 + 1;
      *puVar3 = *puVar6;
    }
  }
  else {
    puVar6 = (undefined2 *)*(undefined4 *)(unaff_BP + 6);
    *puVar6 = 1;
    ((undefined2 *)puVar6)[1] = 0;
  }
  return;
}

