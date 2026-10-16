
void FUN_0000_2885(void)

{
  undefined1 *puVar1;
  undefined2 in_AX;
  int iVar2;
  undefined1 *puVar3;
  undefined2 unaff_CS;
  undefined2 unaff_DS;
  
  *(undefined2 *)0x13f = in_AX;
  puVar3 = (undefined1 *)0x0;
  FUN_0100_17e7();
  for (iVar2 = 0x300; iVar2 != 0; iVar2 = iVar2 + -1) {
    puVar1 = puVar3;
    puVar3 = puVar3 + 1;
    *puVar1 = 0;
  }
  FUN_0100_17e7();
  thunk_FUN_0100_1753();
  return;
}

