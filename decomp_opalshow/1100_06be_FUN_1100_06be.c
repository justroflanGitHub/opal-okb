
void __cdecl16near FUN_1100_06be(void)

{
  undefined2 unaff_DS;
  
  if (*(int *)0x102f < 0) {
    *(undefined2 *)0x102f = 0;
  }
  else if (*(int *)0x1037 - *(int *)0x1033 < *(int *)0x102f) {
    if (*(char *)0x103a == '\0') {
      *(int *)0x102f = *(int *)0x1037 - *(int *)0x1033;
      *(undefined1 *)0x1039 = 1;
    }
    else {
      *(undefined2 *)0x102f = 0;
      *(int *)0x102d = *(int *)0x102d + 1;
    }
  }
  if (*(int *)0x102d < 0) {
    *(undefined2 *)0x102d = 0;
  }
  else if (*(int *)0x1035 - *(int *)0x1031 < *(int *)0x102d) {
    *(int *)0x102d = *(int *)0x1035 - *(int *)0x1031;
    FUN_1100_068a();
  }
  FUN_1100_083e();
  return;
}

