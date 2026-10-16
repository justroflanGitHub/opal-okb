
undefined2 __cdecl16far FUN_144d_0a9a(uint *param_1)

{
  code *pcVar1;
  char cVar2;
  
  pcVar1 = (code *)swi(0x21);
  cVar2 = (*pcVar1)();
  *param_1 = (uint)(byte)(cVar2 + 1);
  return 0;
}

