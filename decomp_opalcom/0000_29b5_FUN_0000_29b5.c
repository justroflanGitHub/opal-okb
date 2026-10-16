
void FUN_0000_29b5(void)

{
  undefined2 uVar1;
  undefined1 *puVar2;
  char *pcVar3;
  char *pcVar4;
  undefined1 *puVar5;
  code *pcVar6;
  int in_CX;
  int iVar7;
  undefined1 *unaff_SI;
  char *pcVar8;
  undefined1 *puVar9;
  undefined1 *unaff_DI;
  char *pcVar10;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  bool bVar11;
  undefined1 *in_stack_0000000c;
  
  while( true ) {
    unaff_SI = unaff_SI + 1;
    in_CX = in_CX + -1;
    if (in_CX == 0) break;
    puVar2 = unaff_DI;
    unaff_DI = unaff_DI + 1;
    *puVar2 = *unaff_SI;
  }
  FUN_0100_185b();
  FUN_0100_1846();
  FUN_0100_191b();
  uVar1 = *(undefined2 *)0x2c;
  pcVar10 = unaff_DI + 4;
  FUN_0100_1722();
  iVar7 = 0x49;
  do {
    if (iVar7 == 0) break;
    iVar7 = iVar7 + -1;
    pcVar3 = pcVar10;
    pcVar10 = pcVar10 + -1;
  } while (*pcVar3 != '\\');
  pcVar10 = pcVar10 + 2;
  pcVar8 = (char *)0x156;
  for (iVar7 = 9; iVar7 != 0; iVar7 = iVar7 + -1) {
    pcVar4 = pcVar10;
    pcVar10 = pcVar10 + 1;
    pcVar3 = pcVar8;
    pcVar8 = pcVar8 + 1;
    *pcVar4 = *pcVar3;
  }
  FUN_0100_18ad();
  FUN_0100_1846();
  thunk_FUN_0100_1761();
  puVar9 = (undefined1 *)0x14a;
  for (iVar7 = 0xb; iVar7 != 0; iVar7 = iVar7 + -1) {
    puVar5 = in_stack_0000000c;
    in_stack_0000000c = in_stack_0000000c + 1;
    puVar2 = puVar9;
    puVar9 = puVar9 + 1;
    *puVar5 = *puVar2;
  }
  pcVar6 = (code *)swi(0x21);
  (*pcVar6)();
  FUN_0100_1800();
  FUN_0100_1846();
  FUN_0100_1751();
  thunk_FUN_0100_1761();
  FUN_0100_1846();
  FUN_0100_191b();
  FUN_0100_191b();
  FUN_0100_191b();
  FUN_0100_191b();
  uVar1 = *(undefined2 *)0x2c;
  pcVar10 = in_stack_0000000c + 4;
  FUN_0100_1722();
  iVar7 = 0x49;
  do {
    if (iVar7 == 0) break;
    iVar7 = iVar7 + -1;
    pcVar3 = pcVar10;
    pcVar10 = pcVar10 + -1;
  } while (*pcVar3 != '\\');
  pcVar10 = pcVar10 + 2;
  *(undefined2 *)0x327 = pcVar10;
  pcVar8 = (char *)0x1b6a;
  for (iVar7 = 0xd; iVar7 != 0; iVar7 = iVar7 + -1) {
    pcVar4 = pcVar10;
    pcVar10 = pcVar10 + 1;
    pcVar3 = pcVar8;
    pcVar8 = pcVar8 + 1;
    *pcVar4 = *pcVar3;
  }
  bVar11 = true;
  pcVar6 = (code *)swi(0x21);
  (*pcVar6)();
  if (!bVar11) {
    FUN_0100_16a3();
  }
  do {
    *(undefined1 *)0x149 = 1;
    FUN_0100_1781();
    FUN_0100_1846();
    unaff_DS = (undefined2)((ulong)*(undefined4 *)0x13b >> 0x10);
    pcVar6 = (code *)swi(0x21);
    (*pcVar6)();
    pcVar6 = (code *)swi(0x21);
    (*pcVar6)();
    if (*(int *)0x143 == 0) {
      return;
    }
    *(undefined2 *)0x143 = 0;
  } while (*(char *)0x149 != '\x01');
  return;
}

