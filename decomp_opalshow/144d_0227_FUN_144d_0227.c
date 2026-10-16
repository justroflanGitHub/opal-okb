
void __cdecl16far FUN_144d_0227(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x3b);
  (*pcVar1)();
  pcVar1 = (code *)swi(0x3d);
  (*pcVar1)();
  return;
}

