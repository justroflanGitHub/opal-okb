
void FUN_0100_181b(void)

{
  code *pcVar1;
  undefined2 unaff_DS;
  bool bVar2;
  
  bVar2 = true;
  pcVar1 = (code *)swi(0x21);
  (*pcVar1)();
  if (!bVar2) {
    FUN_0100_16a3();
  }
  do {
    *(undefined1 *)0x149 = 1;
    FUN_0100_1781();
    FUN_0100_1846();
    unaff_DS = (undefined2)((ulong)*(undefined4 *)0x13b >> 0x10);
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
    if (*(int *)0x143 == 0) {
      return;
    }
    *(undefined2 *)0x143 = 0;
  } while (*(char *)0x149 != '\x01');
  return;
}

