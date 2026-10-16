
void thunk_FUN_0100_1761(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x21);
  (*pcVar1)();
  FUN_0100_1800();
  return;
}

