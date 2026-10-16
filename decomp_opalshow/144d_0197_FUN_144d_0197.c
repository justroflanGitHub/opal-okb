
void FUN_144d_0197(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x3a);
  (*pcVar1)();
  pcVar1 = (code *)swi(1);
  (*pcVar1)();
  return;
}

