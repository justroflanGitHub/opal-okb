
void __cdecl16far FUN_144d_0864(void)

{
  code *pcVar1;
  undefined2 unaff_DS;
  
  if ((char)((uint)*(undefined2 *)0x40e >> 8) == '\0') {
    *(undefined2 *)0x40e = 0xffff;
  }
  else {
    if (*(int *)0x5c0 == -0x292a) {
      (*(code *)*(undefined2 *)0x5c2)();
    }
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
  }
  return;
}

