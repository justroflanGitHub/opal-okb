
void __cdecl16far FUN_144d_018b(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x3a);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

