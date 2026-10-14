
void FUN_1000_6a4b(void)

{
  uint *puVar1;
  undefined2 uVar2;
  uint uVar3;
  undefined2 *puVar4;
  undefined2 *puVar5;
  undefined2 *puVar6;
  undefined2 uVar7;
  undefined2 uVar8;
  undefined2 uVar9;
  undefined2 uVar10;
  undefined2 uVar11;
  int *piVar12;
  int iVar13;
  int unaff_BP;
  undefined2 *puVar14;
  undefined2 *puVar15;
  undefined2 uVar16;
  undefined2 uVar17;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  uVar17 = 0x1000;
  piVar12 = (int *)*(undefined4 *)(unaff_BP + 0x16);
  if (*piVar12 == 0 && ((int *)piVar12)[1] == 0) {
    *(undefined2 *)0x45ce = 1;
    *(undefined2 *)0x45d0 = 0;
    uVar2 = *(undefined2 *)0x2bc4;
    puVar15 = (undefined2 *)0x0;
    puVar14 = (undefined2 *)0x30d;
    for (iVar13 = 0xd; iVar13 != 0; iVar13 = iVar13 + -1) {
      puVar6 = puVar15;
      puVar15 = puVar15 + 1;
      puVar4 = puVar14;
      puVar14 = puVar14 + 1;
      *puVar6 = *puVar4;
    }
    for (iVar13 = 6; iVar13 != 0; iVar13 = iVar13 + -1) {
      puVar4 = puVar15;
      puVar15 = puVar15 + 1;
      *puVar4 = 0x2020;
    }
    *(undefined1 *)puVar15 = 0x20;
    while( true ) {
      *(undefined2 *)(unaff_BP + -0x10) = 3;
      if (*(int *)0x33f0 == 0 && *(int *)0x33f2 == 0) {
        *(undefined2 *)(unaff_BP + -0x10) = 2;
      }
      iVar13 = *(int *)(unaff_BP + -0x10) * 0xc;
      uVar2 = *(undefined2 *)0x2bc8;
      uVar7 = *(undefined2 *)0x2bc4;
      *(undefined2 *)0x13 = *(undefined2 *)(iVar13 + -9);
      *(undefined2 *)0x15 = *(undefined2 *)(iVar13 + -7);
      *(undefined2 *)0x17 = *(undefined2 *)(iVar13 + -5);
      if (*(int *)0x340c != 0 || *(int *)0x340e != 0) {
        puVar14 = (undefined2 *)(*(int *)0x34ca * 0x14 + 0x2e5);
        puVar15 = (undefined2 *)0x27;
        for (iVar13 = 10; iVar13 != 0; iVar13 = iVar13 + -1) {
          puVar6 = puVar15;
          puVar15 = puVar15 + 1;
          puVar4 = puVar14;
          puVar14 = puVar14 + 1;
          *puVar6 = *puVar4;
        }
        for (iVar13 = 9; iVar13 != 0; iVar13 = iVar13 + -1) {
          puVar4 = puVar15;
          puVar15 = puVar15 + 1;
          *puVar4 = 0x2020;
        }
        *(undefined1 *)puVar15 = 0x20;
        *(undefined2 *)0x45ce = 2;
        *(undefined2 *)0x45d0 = 0;
      }
      *(undefined2 *)(unaff_BP + -2) = 0x27;
      uVar2 = *(undefined2 *)(unaff_BP + 0x10);
      uVar7 = *(undefined2 *)(unaff_BP + 0xe);
      uVar8 = *(undefined2 *)(unaff_BP + 8);
      uVar9 = *(undefined2 *)(unaff_BP + 6);
      uVar10 = *(undefined2 *)(unaff_BP + 0xc);
      uVar11 = *(undefined2 *)(unaff_BP + 10);
      *(int *)0x1944 = unaff_BP + -4;
      *(undefined2 *)0x1946 = unaff_SS;
      uVar16 = 0xff9;
      FUN_1000_6a34(uVar17,0x45be,unaff_DS,0x45c6,unaff_DS,0,0x52a6,uVar11,uVar10,uVar9,uVar8,0x45ce
                    ,unaff_DS,uVar7,uVar2,0,0x506e);
      piVar12 = (int *)*(undefined4 *)(unaff_BP + 10);
      if (*piVar12 != 100) break;
      if (((int *)piVar12)[1] != 0) {
        FUN_1000_7506();
        return;
      }
      if ((*(int *)0x45c6 == 1) && (*(int *)0x45c8 == 0)) {
        if (*(int *)0x33f0 == 0 && *(int *)0x33f2 == 0) {
          *(undefined2 *)0x33f0 = 1;
          *(undefined2 *)0x33f2 = 0;
        }
        else {
          *(undefined2 *)0x33f2 = 0;
          *(undefined2 *)0x33f0 = 0;
        }
      }
      uVar17 = uVar16;
      if ((*(int *)0x45c6 == 2) && (*(int *)0x45c8 == 0)) {
        if (*(int *)0x34ca == 0 && *(int *)0x34cc == 0) {
          *(undefined2 *)0x34ca = 1;
          *(undefined2 *)0x34cc = 0;
        }
        else {
          *(undefined2 *)0x34cc = 0;
          *(undefined2 *)0x34ca = 0;
        }
      }
    }
    FUN_1000_7506();
    return;
  }
  *(undefined2 *)0x45ce = 2;
  *(undefined2 *)0x45d0 = 0;
  uVar2 = *(undefined2 *)0x2bc4;
  puVar15 = (undefined2 *)0x0;
  puVar14 = (undefined2 *)0x39f;
  for (iVar13 = 10; iVar13 != 0; iVar13 = iVar13 + -1) {
    puVar6 = puVar15;
    puVar15 = puVar15 + 1;
    puVar4 = puVar14;
    puVar14 = puVar14 + 1;
    *puVar6 = *puVar4;
  }
  puVar5 = (undefined2 *)((int)puVar15 + 1);
  *(undefined1 *)puVar15 = *(undefined1 *)puVar14;
  for (iVar13 = 9; iVar13 != 0; iVar13 = iVar13 + -1) {
    puVar4 = puVar5;
    puVar5 = puVar5 + 1;
    *puVar4 = 0x2020;
  }
  puVar15 = (undefined2 *)0x27;
  puVar14 = (undefined2 *)0x3b4;
  for (iVar13 = 10; iVar13 != 0; iVar13 = iVar13 + -1) {
    puVar6 = puVar15;
    puVar15 = puVar15 + 1;
    puVar4 = puVar14;
    puVar14 = puVar14 + 1;
    *puVar6 = *puVar4;
  }
  puVar5 = (undefined2 *)((int)puVar15 + 1);
  *(undefined1 *)puVar15 = *(undefined1 *)puVar14;
  for (iVar13 = 9; iVar13 != 0; iVar13 = iVar13 + -1) {
    puVar4 = puVar5;
    puVar5 = puVar5 + 1;
    *puVar4 = 0x2020;
  }
LAB_1000_6c02:
  do {
    uVar3 = *(uint *)0x0;
    iVar13 = *(int *)0x2;
    *(int *)(unaff_BP + -0x1a) = uVar3 + 1;
    *(int *)(unaff_BP + -0x18) = iVar13 + (uint)(0xfffe < uVar3);
    *(undefined2 *)(unaff_BP + -2) = 3;
    *(int *)0x1944 = unaff_BP + -4;
    *(undefined2 *)0x1946 = unaff_SS;
    FUN_1000_6923(uVar17,unaff_BP + -0x1a);
    uVar17 = *(undefined2 *)0x2bcc;
    puVar14 = (undefined2 *)(*(int *)0x34d4 * 10 + 0x1f2);
    uVar2 = *(undefined2 *)0x2bc4;
    puVar15 = (undefined2 *)0x31;
    for (iVar13 = 5; iVar13 != 0; iVar13 = iVar13 + -1) {
      puVar6 = puVar15;
      puVar15 = puVar15 + 1;
      puVar4 = puVar14;
      puVar14 = puVar14 + 1;
      *puVar6 = *puVar4;
    }
    *(undefined2 *)(unaff_BP + -2) = 0x27;
    uVar2 = *(undefined2 *)(unaff_BP + 0x10);
    uVar7 = *(undefined2 *)(unaff_BP + 0xe);
    uVar8 = *(undefined2 *)(unaff_BP + 8);
    uVar9 = *(undefined2 *)(unaff_BP + 6);
    uVar10 = *(undefined2 *)(unaff_BP + 0xc);
    uVar11 = *(undefined2 *)(unaff_BP + 10);
    *(int *)0x1944 = unaff_BP + -4;
    *(undefined2 *)0x1946 = unaff_SS;
    uVar17 = 0xff9;
    FUN_1000_6a34(0xff9,0x45be,unaff_DS,0x45c6,unaff_DS,0,0x52a6,uVar11,uVar10,uVar9,uVar8,0x45ce,
                  unaff_DS,uVar7,uVar2,0,0x506e);
    piVar12 = (int *)*(undefined4 *)(unaff_BP + 10);
    if (*piVar12 != 100) {
      FUN_1000_7506();
      return;
    }
    if (((int *)piVar12)[1] != 0) {
      FUN_1000_7506();
      return;
    }
    if ((*(int *)0x45c6 == 2) && (*(int *)0x45c8 == 0)) {
      puVar1 = (uint *)0x34d4;
      uVar3 = *puVar1;
      *puVar1 = *puVar1 + 1;
      *(int *)0x34d6 = *(int *)0x34d6 + (uint)(0xfffe < uVar3);
      if ((-1 < *(int *)0x34d6) && ((0 < *(int *)0x34d6 || (4 < *(uint *)0x34d4)))) {
        *(undefined2 *)0x34d4 = 1;
        *(undefined2 *)0x34d6 = 0;
      }
    }
  } while ((*(int *)0x45c6 != 1) || (*(int *)0x45c8 != 0));
  if ((*(int *)0x34c6 != 10) || (*(int *)0x34c8 != 0)) goto LAB_1000_6d2f;
  *(undefined2 *)0x34c6 = 1;
  goto LAB_1000_6d26;
LAB_1000_6d2f:
  puVar1 = (uint *)0x34c6;
  uVar3 = *puVar1;
  *puVar1 = *puVar1 + 1;
  *(int *)0x34c8 = *(int *)0x34c8 + (uint)(0xfffe < uVar3);
  iVar13 = *(int *)0x2 + (uint)(0xfffe < *(uint *)0x0);
  if ((iVar13 <= *(int *)0x34c8) &&
     ((iVar13 < *(int *)0x34c8 || (*(uint *)0x0 + 1 < *(uint *)0x34c6)))) {
    *(undefined2 *)0x34c6 = 10;
LAB_1000_6d26:
    *(undefined2 *)0x34c8 = 0;
  }
  goto LAB_1000_6c02;
}

