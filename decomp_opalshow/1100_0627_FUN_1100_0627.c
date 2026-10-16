
void FUN_1100_0627(void)

{
  code *pcVar1;
  char in_DH;
  undefined2 unaff_SS;
  
  if (*(byte *)0x1035 < (byte)(in_DH + 1U)) {
    FUN_1100_068a();
  }
  pcVar1 = (code *)swi(0x10);
  (*pcVar1)();
  *(undefined1 *)0x1039 = 0;
  return;
}

