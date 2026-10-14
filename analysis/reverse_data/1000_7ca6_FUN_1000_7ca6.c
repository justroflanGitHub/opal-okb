
void __stdcall16far FUN_1000_7ca6(void)

{
  uint *puVar1;
  uint uVar2;
  char cVar3;
  int iVar4;
  int unaff_BP;
  undefined2 uVar5;
  undefined2 uVar6;
  undefined2 uVar7;
  undefined2 unaff_SS;
  
  uVar5 = 0x1000;
  if (*(char *)(unaff_BP + -4) == '\x1f') {
    *(int *)(unaff_BP + -8) = *(int *)(unaff_BP + -8) + 2;
  }
  else {
    iVar4 = (uint)*(byte *)(unaff_BP + -4) * 4;
    *(int *)(unaff_BP + -10) = iVar4;
    if ((*(byte *)(iVar4 + (int)*(undefined4 *)(unaff_BP + -0xe)) & 1) == 1) {
      uVar5 = 0x2e73;
      func_0x0003944b(0x1000,*(undefined2 *)(unaff_BP + -6),*(undefined2 *)(unaff_BP + -8));
    }
    uVar6 = uVar5;
    if ((*(byte *)(*(int *)(unaff_BP + -10) + (int)*(undefined4 *)(unaff_BP + -0xe)) & 2) == 2) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 1,*(undefined2 *)(unaff_BP + -8));
    }
    uVar5 = uVar6;
    if ((*(byte *)(*(int *)(unaff_BP + -10) + (int)*(undefined4 *)(unaff_BP + -0xe)) & 4) == 4) {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 2,*(undefined2 *)(unaff_BP + -8));
    }
    uVar6 = uVar5;
    if ((*(byte *)(*(int *)(unaff_BP + -10) + (int)*(undefined4 *)(unaff_BP + -0xe)) & 8) == 8) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 3,*(undefined2 *)(unaff_BP + -8));
    }
    uVar5 = uVar6;
    if ((*(byte *)(*(int *)(unaff_BP + -10) + (int)*(undefined4 *)(unaff_BP + -0xe)) & 0x10) == 0x10
       ) {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 4,*(undefined2 *)(unaff_BP + -8));
    }
    uVar6 = uVar5;
    if ((*(byte *)(*(int *)(unaff_BP + -10) + (int)*(undefined4 *)(unaff_BP + -0xe)) & 0x20) == 0x20
       ) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(undefined2 *)(unaff_BP + -6),*(int *)(unaff_BP + -8) + -1);
    }
    uVar5 = uVar6;
    if ((*(byte *)(*(int *)(unaff_BP + -10) + (int)*(undefined4 *)(unaff_BP + -0xe)) & 0x40) == 0x40
       ) {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 1,*(int *)(unaff_BP + -8) + -1);
    }
    uVar6 = uVar5;
    if ((*(byte *)(*(int *)(unaff_BP + -10) + (int)*(undefined4 *)(unaff_BP + -0xe)) & 0x80) == 0x80
       ) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 2,*(int *)(unaff_BP + -8) + -1);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 1) == 1)
    {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 3,*(int *)(unaff_BP + -8) + -1);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 2) == 2)
    {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 4,*(int *)(unaff_BP + -8) + -1);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 4) == 4)
    {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(undefined2 *)(unaff_BP + -6),*(int *)(unaff_BP + -8) + -2);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 8) == 8)
    {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 1,*(int *)(unaff_BP + -8) + -2);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x10) ==
        0x10) {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 2,*(int *)(unaff_BP + -8) + -2);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x20) ==
        0x20) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 3,*(int *)(unaff_BP + -8) + -2);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x40) ==
        0x40) {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 4,*(int *)(unaff_BP + -8) + -2);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x80) ==
        0x80) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(undefined2 *)(unaff_BP + -6),*(int *)(unaff_BP + -8) + -3);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 1) == 1)
    {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 1,*(int *)(unaff_BP + -8) + -3);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 2) == 2)
    {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 2,*(int *)(unaff_BP + -8) + -3);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 4) == 4)
    {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 3,*(int *)(unaff_BP + -8) + -3);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 8) == 8)
    {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 4,*(int *)(unaff_BP + -8) + -3);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x10) ==
        0x10) {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(undefined2 *)(unaff_BP + -6),*(int *)(unaff_BP + -8) + -4);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x20) ==
        0x20) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 1,*(int *)(unaff_BP + -8) + -4);
    }
    uVar5 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x40) ==
        0x40) {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 2,*(int *)(unaff_BP + -8) + -4);
    }
    uVar6 = uVar5;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x80) ==
        0x80) {
      uVar6 = 0x2e73;
      func_0x0003944b(uVar5,*(int *)(unaff_BP + -6) + 3,*(int *)(unaff_BP + -8) + -4);
    }
    uVar7 = uVar6;
    if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 3) & 1) == 1)
    {
      uVar7 = 0x2e73;
      func_0x0003944b(uVar6,*(int *)(unaff_BP + -6) + 4,*(int *)(unaff_BP + -8) + -4);
    }
    uVar5 = uVar7;
    if (*(char *)(unaff_BP + -4) == '_') {
      uVar5 = 0x2e73;
      func_0x0003944b(uVar7,*(int *)(unaff_BP + -6) + 5,*(int *)(unaff_BP + -8) + -2);
    }
    *(int *)(unaff_BP + -6) = *(int *)(unaff_BP + -6) + 6;
  }
  while( true ) {
    puVar1 = (uint *)(unaff_BP + -0x12);
    uVar2 = *puVar1;
    *puVar1 = *puVar1 + 1;
    *(int *)(unaff_BP + -0x10) = *(int *)(unaff_BP + -0x10) + (uint)(0xfffe < uVar2);
    iVar4 = (int)*(uint *)*(undefined4 *)(unaff_BP + 0x12) >> 0xf;
    if ((iVar4 < *(int *)(unaff_BP + -0x10)) ||
       ((iVar4 <= *(int *)(unaff_BP + -0x10) &&
        (*(uint *)*(undefined4 *)(unaff_BP + 0x12) <= *(uint *)(unaff_BP + -0x12))))) break;
    cVar3 = func_0x00036efa(uVar5,*(undefined1 *)
                                   (*(int *)(unaff_BP + -0x12) +
                                   (int)*(undefined4 *)(unaff_BP + 0x16)));
    *(char *)(unaff_BP + -4) = cVar3;
    if (cVar3 != '\x1e') {
      FUN_1000_7ca6();
      return;
    }
    *(int *)(unaff_BP + -8) = *(int *)(unaff_BP + -8) + -2;
    uVar5 = 0x2e73;
  }
  FUN_3000_9150(uVar5,*(undefined2 *)(unaff_BP + -2));
  return;
}

