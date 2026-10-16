
void FUN_0100_185b(void)

{
  undefined1 *puVar1;
  code *pcVar2;
  undefined2 uVar3;
  int iVar4;
  undefined1 *puVar5;
  undefined2 unaff_CS;
  undefined2 unaff_DS;
  undefined1 in_CF;
  
  pcVar2 = (code *)swi(0x21);
  uVar3 = (*pcVar2)();
  if ((bool)in_CF) {
    pcVar2 = (code *)swi(0x21);
    (*pcVar2)();
    uVar3 = FUN_0100_1800();
    if (!(bool)in_CF) {
      *(undefined2 *)0x13f = uVar3;
      FUN_0100_17e7();
      FUN_0100_1751();
    }
  }
  else {
    *(undefined2 *)0x13f = uVar3;
    puVar5 = (undefined1 *)0x0;
    FUN_0100_17e7();
    for (iVar4 = 0x300; iVar4 != 0; iVar4 = iVar4 + -1) {
      puVar1 = puVar5;
      puVar5 = puVar5 + 1;
      *puVar1 = 0;
    }
    FUN_0100_17e7();
    thunk_FUN_0100_1753();
  }
  return;
}

