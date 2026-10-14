
undefined2 __stdcall16far FUN_4000_6fac(void)

{
  code *pcVar1;
  
  pcVar1 = (code *)swi(0x21);
  (*pcVar1)();
  return 0;
}

