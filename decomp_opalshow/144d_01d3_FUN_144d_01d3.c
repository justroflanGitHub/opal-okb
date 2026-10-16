
void __cdecl16far FUN_144d_01d3(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x39);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

