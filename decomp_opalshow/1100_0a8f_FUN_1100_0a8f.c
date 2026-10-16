
void __cdecl16near FUN_1100_0a8f(void)

{
  undefined2 in_CX;
  undefined2 extraout_DX;
  undefined2 unaff_DS;
  undefined1 in_ZF;
  
  *(undefined2 *)0x10f4 = 0;
  FUN_1100_0f84();
  if ((bool)in_ZF) {
    return;
  }
  FUN_1100_0f79();
  *(undefined2 *)0x10f6 = in_CX;
  *(undefined2 *)0x10f8 = extraout_DX;
  *(undefined2 *)0x10fa = 0;
  *(undefined2 *)0x10fe = 0;
  *(undefined2 *)0x1102 = 0;
  *(undefined2 *)0x1104 = 0;
  *(undefined2 *)0x10fc = in_CX;
  *(undefined2 *)0x1100 = extraout_DX;
  FUN_1100_103f();
  FUN_1100_0a2c();
  (*(code *)*(undefined2 *)0x30c)();
  FUN_144d_0010();
  return;
}

