
void __cdecl16far FUN_144d_01bb(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x39);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

