
void __cdecl16far FUN_144d_0233(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x37);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

