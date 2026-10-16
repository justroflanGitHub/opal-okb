
void __cdecl16far FUN_144d_026f(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x34);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

