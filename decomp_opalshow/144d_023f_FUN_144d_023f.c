
void __cdecl16far FUN_144d_023f(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x3b);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

