
void __cdecl16near FUN_1100_0638(void)

{
  code *pcVar1;
  undefined2 unaff_SS;
  
  pcVar1 = (code *)swi(0x10);
  (*pcVar1)();
  *(undefined1 *)0x1039 = 0;
  return;
}

