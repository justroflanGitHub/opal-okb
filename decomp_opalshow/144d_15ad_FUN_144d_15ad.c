
void FUN_144d_15ad(void)

{
  code *pcVar1;
  int unaff_BP;
  undefined2 unaff_SS;
  
  if (*(int *)(unaff_BP + 0xc) != 0) {
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
    FUN_144d_0ac1();
    return;
  }
  FUN_144d_0ac1();
  return;
}

