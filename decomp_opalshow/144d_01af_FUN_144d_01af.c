
void __cdecl16far FUN_144d_01af(void)

{
  code *pcVar1;
  int in_CX;
  char in_ZF;
  
  pcVar1 = (code *)swi(0x35);
  (*pcVar1)();
  if (in_CX == 1 || in_ZF != '\0') {
    return;
  }
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

