
void __stdcall16far FUN_1000_7df9(void)

{
  uint *puVar1;
  uint uVar2;
  char cVar3;
  int iVar4;
  int unaff_BP;
  undefined2 unaff_SS;
  
  func_0x0003944b(0x1000,*(int *)(unaff_BP + -6) + 4);
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 4) == 4) {
    func_0x0003944b(0x2e73,*(undefined2 *)(unaff_BP + -6),*(int *)(unaff_BP + -8) + -2);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 8) == 8) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 1,*(int *)(unaff_BP + -8) + -2);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x10) ==
      0x10) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 2,*(int *)(unaff_BP + -8) + -2);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x20) ==
      0x20) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 3,*(int *)(unaff_BP + -8) + -2);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x40) ==
      0x40) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 4,*(int *)(unaff_BP + -8) + -2);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 1) & 0x80) ==
      0x80) {
    func_0x0003944b(0x2e73,*(undefined2 *)(unaff_BP + -6),*(int *)(unaff_BP + -8) + -3);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 1) == 1) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 1,*(int *)(unaff_BP + -8) + -3);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 2) == 2) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 2,*(int *)(unaff_BP + -8) + -3);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 4) == 4) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 3,*(int *)(unaff_BP + -8) + -3);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 8) == 8) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 4,*(int *)(unaff_BP + -8) + -3);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x10) ==
      0x10) {
    func_0x0003944b(0x2e73,*(undefined2 *)(unaff_BP + -6),*(int *)(unaff_BP + -8) + -4);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x20) ==
      0x20) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 1,*(int *)(unaff_BP + -8) + -4);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x40) ==
      0x40) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 2,*(int *)(unaff_BP + -8) + -4);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 2) & 0x80) ==
      0x80) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 3,*(int *)(unaff_BP + -8) + -4);
  }
  if ((*(byte *)((int)*(undefined4 *)(unaff_BP + -0xe) + *(int *)(unaff_BP + -10) + 3) & 1) == 1) {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 4,*(int *)(unaff_BP + -8) + -4);
  }
  if (*(char *)(unaff_BP + -4) == '_') {
    func_0x0003944b(0x2e73,*(int *)(unaff_BP + -6) + 5,*(int *)(unaff_BP + -8) + -2);
  }
  *(int *)(unaff_BP + -6) = *(int *)(unaff_BP + -6) + 6;
  while( true ) {
    puVar1 = (uint *)(unaff_BP + -0x12);
    uVar2 = *puVar1;
    *puVar1 = *puVar1 + 1;
    *(int *)(unaff_BP + -0x10) = *(int *)(unaff_BP + -0x10) + (uint)(0xfffe < uVar2);
    iVar4 = (int)*(uint *)*(undefined4 *)(unaff_BP + 0x12) >> 0xf;
    if ((iVar4 < *(int *)(unaff_BP + -0x10)) ||
       ((iVar4 <= *(int *)(unaff_BP + -0x10) &&
        (*(uint *)*(undefined4 *)(unaff_BP + 0x12) <= *(uint *)(unaff_BP + -0x12))))) break;
    cVar3 = func_0x00036efa(0x2e73,*(undefined1 *)
                                    (*(int *)(unaff_BP + -0x12) +
                                    (int)*(undefined4 *)(unaff_BP + 0x16)));
    *(char *)(unaff_BP + -4) = cVar3;
    if (cVar3 != '\x1e') {
      FUN_1000_7ca6();
      return;
    }
    *(int *)(unaff_BP + -8) = *(int *)(unaff_BP + -8) + -2;
  }
  FUN_3000_9150(0x2e73,*(undefined2 *)(unaff_BP + -2));
  return;
}

