
void FUN_0100_1846(void)

{
  code *pcVar1;
  undefined2 unaff_DS;
  
  while ((*(int *)0x143 != 0 && (*(undefined2 *)0x143 = 0, *(char *)0x149 != '\x01'))) {
    *(undefined1 *)0x149 = 1;
    FUN_0100_1781();
    FUN_0100_1846();
    unaff_DS = (undefined2)((ulong)*(undefined4 *)0x13b >> 0x10);
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
  }
  return;
}

