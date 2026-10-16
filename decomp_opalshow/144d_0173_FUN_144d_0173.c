
void FUN_144d_0173(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x3a);
  (*pcVar1)();
  FUN_15fd_2448();
  return;
}

