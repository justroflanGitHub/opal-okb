
void __cdecl16far FUN_144d_017f(void)

{
  code *pcVar1;
  int in_CX;
  char in_ZF;
  
  pcVar1 = (code *)swi(0x3a);
  (*pcVar1)();
  if (in_CX == 1 || in_ZF == '\0') {
    return;
  }
  return;
}

