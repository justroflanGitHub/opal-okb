
void FUN_0000_2956(void)

{
  int in_BX;
  int unaff_DI;
  undefined2 unaff_ES;
  
  do {
    in_BX = in_BX + 1;
  } while (*(char *)(in_BX + unaff_DI) == ' ');
  FUN_0100_1722(unaff_DI + in_BX);
  return;
}

