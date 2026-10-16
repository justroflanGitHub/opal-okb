
void __cdecl16far FUN_144d_0257(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x35);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

