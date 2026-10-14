
void FUN_1000_1bfd(void)

{
  uint uVar1;
  uint *puVar2;
  int *piVar3;
  int iVar4;
  int iVar5;
  int iVar6;
  int unaff_BP;
  int iVar7;
  undefined2 uVar8;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  uVar8 = 0x1000;
  while( true ) {
    if (*(int *)(unaff_BP + -0x32) < *(int *)(unaff_BP + -4)) {
      FUN_1000_2100();
      return;
    }
    if (*(int *)(unaff_BP + -4) == *(int *)0x445a) break;
    iVar5 = *(int *)(unaff_BP + -4) * 4;
    FUN_3000_2225(uVar8);
    func_0x000322a3(0x2e73);
    FUN_3000_2225(0x2e73);
    func_0x000322a3(0x2e73);
    iVar7 = *(int *)(iVar5 + 0x56c);
    if (*(int *)(iVar5 + 0x56e) < 0) {
      iVar7 = -iVar7;
    }
    *(int *)(unaff_BP + -10) = iVar7;
    *(int *)(unaff_BP + -10) = *(int *)(unaff_BP + -10) + (iVar7 / 100) * -100;
    if ((*(int *)(unaff_BP + -4) == 1) && (*(int *)(unaff_BP + -10) != 0)) {
      func_0x0003231b(0x2e73);
      func_0x00032357(0x2e73);
      FUN_3000_2231(0x2e73);
    }
    if (*(int *)(unaff_BP + -10) != 99) {
      func_0x0003231b(0x2e73);
      FUN_3000_2384(0x2e73);
      func_0x000322a3(0x2e73);
    }
    if ((*(int *)(unaff_BP + -10) == 0) || (*(int *)(unaff_BP + -10) == 99)) {
      func_0x0003231b(0x2e73);
      func_0x00032279(0x2e73);
      func_0x000322a3(0x2e73);
    }
    uVar8 = 0x2e73;
    if (*(int *)(unaff_BP + -10) == 0) {
      piVar3 = (int *)*(undefined4 *)(unaff_BP + 0x1a);
      if (*piVar3 == 0 && ((int *)piVar3)[1] == 0) {
        iVar7 = *(int *)(unaff_BP + -4) * 4;
        FUN_3000_2225(0x2e73);
        func_0x000322d0(0x2e73,*(undefined2 *)0x2b48,iVar7 + 0x38c);
        func_0x000322a3(0x2e73);
        FUN_3000_2225(0x2e73);
        func_0x000322d0(0x2e73,*(undefined2 *)0x2b48,iVar7 + 0x3a4);
        uVar8 = 0x2e73;
        func_0x000322a3(0x2e73);
      }
      break;
    }
    piVar3 = (int *)(unaff_BP + -4);
    iVar7 = *piVar3;
    *piVar3 = *piVar3 + 1;
    if (SCARRY2(iVar7,1)) {
      FUN_1000_2100();
      return;
    }
  }
  puVar2 = (uint *)*(undefined4 *)(unaff_BP + 0xe);
  if ((-1 < (int)((uint *)puVar2)[1]) && ((0 < (int)((uint *)puVar2)[1] || (1 < *puVar2)))) {
    piVar3 = (int *)*(undefined4 *)(unaff_BP + 0x2a);
    if ((*piVar3 != 1) || (((int *)piVar3)[1] != 0)) {
      iVar7 = *(int *)*(undefined4 *)(unaff_BP + 0xe);
      *(int *)(unaff_BP + -0x30) = iVar7;
      *(undefined2 *)(unaff_BP + -8) = 2;
      if (1 < iVar7) {
        iVar4 = *(int *)(unaff_BP + -4) * 4;
        *(int *)(unaff_BP + -0x36) = iVar4;
        *(int *)(unaff_BP + -0x2e) = iVar4 + 0x2e4;
        *(undefined2 *)(unaff_BP + -0x2c) = 0x4ed2;
        *(int *)(unaff_BP + -0x2a) = iVar4;
        *(int *)(unaff_BP + -0x20) = iVar4 + 0x23c;
        *(undefined2 *)(unaff_BP + -0x1e) = 0x4ed2;
        iVar5 = iVar4 + 0x270;
        iVar4 = iVar4 + 0x318;
        iVar7 = *(int *)(unaff_BP + -0x30);
        iVar6 = iVar7 + -1;
        iVar7 = (iVar7 >> 0xf) - (uint)(iVar7 == 0);
        *(int *)(unaff_BP + -0x12) = iVar6;
        *(int *)(unaff_BP + -0x10) = iVar7;
        *(int *)(unaff_BP + -8) = *(int *)(unaff_BP + -8) + iVar6;
        *(int *)(unaff_BP + -0x24) = iVar6;
        *(int *)(unaff_BP + -0x34) = iVar7;
        *(int *)(unaff_BP + -0x24) = -*(int *)(unaff_BP + -0x24);
        piVar3 = (int *)(unaff_BP + -0x24);
        iVar7 = *piVar3;
        *piVar3 = -*piVar3;
        *(int *)(unaff_BP + -0x34) = *(int *)(unaff_BP + -0x34) + -1 + (uint)(iVar7 != 0);
        do {
          do {
            func_0x00032294(uVar8);
            func_0x000322ee(0x2e73,*(undefined2 *)0x2b48,iVar5 + -0x1c);
            func_0x000322a3(0x2e73);
            func_0x00032294(0x2e73);
            func_0x000322ee(0x2e73,*(undefined2 *)0x2b48,iVar4 + -0x1c);
            uVar8 = 0x2e73;
            func_0x000322a3(0x2e73);
            iVar5 = iVar5 + 0x18;
            iVar4 = iVar4 + 0x18;
            piVar3 = (int *)(unaff_BP + -0x24);
            *piVar3 = *piVar3 + -1;
          } while (*piVar3 != 0);
          piVar3 = (int *)(unaff_BP + -0x34);
          *piVar3 = *piVar3 + -1;
        } while (-1 < *piVar3);
      }
    }
  }
  puVar2 = (uint *)*(undefined4 *)(unaff_BP + 0xe);
  uVar1 = *puVar2;
  *(uint *)(unaff_BP + -6) = uVar1;
  if ((-1 < (int)((uint *)puVar2)[1]) && ((0 < (int)((uint *)puVar2)[1] || (2 < uVar1)))) {
    *(int *)(unaff_BP + -6) = *(int *)(unaff_BP + -6) + 2;
    iVar7 = *(int *)(unaff_BP + -4) * 4;
    *(int *)(unaff_BP + -0x2e) = *(int *)*(undefined4 *)(unaff_BP + 0x26) * 0x18 + iVar7 + 0x3ec;
    *(undefined2 *)(unaff_BP + -0x2c) = 0x4ed2;
    *(int *)(unaff_BP + -0x20) = *(int *)*(undefined4 *)(unaff_BP + 0x22) * 0x18 + iVar7 + 0x3ec;
    *(undefined2 *)(unaff_BP + -0x1e) = 0x4ed2;
    *(int *)(unaff_BP + -0x36) = uVar1 * 0x18 + iVar7;
    func_0x00032294(uVar8);
    FUN_3000_22df(0x2e73);
    func_0x000322a3(0x2e73);
    func_0x00032294(0x2e73);
    func_0x000322c1(0x2e73);
    func_0x00032279(0x2e73);
    func_0x000322a3(0x2e73);
    iVar7 = *(int *)(unaff_BP + -4) * 4;
    *(int *)(unaff_BP + -0x36) = *(int *)*(undefined4 *)(unaff_BP + 0x22) * 0x18 + iVar7;
    *(int *)(unaff_BP + -0x34) = *(int *)*(undefined4 *)(unaff_BP + 0xe) * 0x18 + iVar7;
    func_0x00032294(0x2e73);
    FUN_3000_22df(0x2e73);
    func_0x000322a3(0x2e73);
    func_0x00032294(0x2e73);
    func_0x000322c1(0x2e73);
    func_0x00032279(0x2e73);
    func_0x000322a3(0x2e73);
    piVar3 = (int *)*(undefined4 *)(unaff_BP + 0x2a);
    if ((*piVar3 != 1) || (((int *)piVar3)[1] != 0)) {
      func_0x00032294(0x2e73);
      FUN_3000_22df(0x2e73);
      func_0x000322a3(0x2e73);
      iVar7 = *(int *)(unaff_BP + -4) * 4;
      *(int *)(unaff_BP + -0x36) = *(int *)*(undefined4 *)(unaff_BP + 0x22) * 0x18 + iVar7;
      *(int *)(unaff_BP + -0x34) = *(int *)*(undefined4 *)(unaff_BP + 0xe) * 0x18 + iVar7;
      func_0x00032294(0x2e73);
      FUN_3000_22df(0x2e73);
      func_0x000322a3(0x2e73);
      func_0x00032294(0x2e73);
      func_0x000322c1(0x2e73);
      func_0x00032279(0x2e73);
      func_0x000322a3(0x2e73);
      func_0x00032294(0x2e73);
      func_0x000322c1(0x2e73);
      func_0x00032279(0x2e73);
      func_0x000322a3(0x2e73);
    }
  }
  *(undefined2 *)(unaff_BP + -0x2a) = *(undefined2 *)(unaff_BP + -6);
  *(undefined2 *)(unaff_BP + -8) = 1;
  FUN_1000_1ab8();
  return;
}

